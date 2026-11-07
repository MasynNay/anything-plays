"""Bounded stereo PCM buffering between a Libretro worker and PortAudio.

When the output device is unavailable, gameplay must continue silently. Oldest
chunks are dropped when audio falls behind instead of blocking emulation.
"""

import ctypes as C
from queue import Empty, Full, Queue
import sys

import numpy as np

try:
    import sounddevice as sd
except (ImportError, OSError):
    # Linux may have the Python package but no system PortAudio library.
    sd = None


SAMPLE_BLOCK_FRAMES = 256
# Reject nonsensical batch lengths before reading native pointers. A core
# callback must not be able to request a multi-gigabyte NumPy view.
MAX_AUDIO_BATCH_FRAMES = 192_000
# Avoid huge interpolated arrays for cores using long native audio batches.
RESAMPLE_INPUT_CHUNK = 2048
NORMAL_DEVICE_RATES = frozenset((
    8000, 11025, 16000, 22050, 32000, 44100, 48000, 88200, 96000,
))


class AudioSink:
    """Keep the core's audio callbacks independent from the output device."""

    def __init__(self):
        self.chunks = Queue(maxsize=32)
        self.pending = np.empty((0, 2), dtype=np.int16)
        self.position = 0
        self.stream = None
        self.output_error = None
        self.output_active = False
        self.source_sample_rate = None
        self.output_sample_rate = None
        self._resample_step = None
        self._resample_next = 0.0
        self._resample_consumed = 0
        self._resample_tail = None
        # Some Libretro cores send individual samples instead of batches.
        # Avoid creating 44,100 NumPy arrays / queue entries per second.
        self._single_samples = np.empty(
            (SAMPLE_BLOCK_FRAMES, 2), dtype=np.int16
        )
        self._single_count = 0

    def _resample(self, chunk):
        """Convert native stereo samples without resetting phase per batch.

        A GB/GBC core commonly reports 131072 Hz, which ordinary 48-kHz
        sound devices reject. This bounded linear interpolation operates only
        on newly submitted frames, preserving fractional phase and the last
        source sample across CoreSession callback boundaries. It does not
        buffer an unbounded history or change emulator timing.
        """
        step = self._resample_step
        if step is None:
            return chunk
        size = len(chunk)
        if not size:
            return chunk
        base = self._resample_consumed
        last = base + size - 1
        prior = self._resample_tail
        lower = base - 1 if prior is not None else base
        begin = max(self._resample_next, float(lower))
        if begin < last:
            count = int(np.ceil((last - begin) / step))
            positions = begin + step * np.arange(count, dtype=np.float64)
            positions = positions[positions < last]
            if len(positions):
                coords = np.floor(positions).astype(np.int64)
                fraction = (positions - coords)[:, np.newaxis]
                if prior is None:
                    extended = chunk
                    indices = coords - base
                else:
                    extended = np.concatenate((prior[np.newaxis, :], chunk), axis=0)
                    indices = coords - (base - 1)
                left = extended[indices].astype(np.float64)
                right = extended[indices + 1].astype(np.float64)
                converted = np.clip(
                    np.rint(left + fraction * (right - left)),
                    -32768, 32767,
                ).astype(np.int16)
                self._resample_next = float(positions[-1] + step)
            else:
                converted = np.empty((0, 2), dtype=np.int16)
        else:
            converted = np.empty((0, 2), dtype=np.int16)
        self._resample_tail = chunk[-1].copy()
        self._resample_consumed = base + size
        return converted

    def push(self, samples):
        if not len(samples):
            return
        chunk = np.asarray(samples, dtype=np.int16).reshape(-1, 2).copy()
        if self._resample_step is not None:
            converted = [
                self._resample(chunk[start:start + RESAMPLE_INPUT_CHUNK])
                for start in range(0, len(chunk), RESAMPLE_INPUT_CHUNK)
            ]
            chunk = np.concatenate(converted, axis=0)
        if not len(chunk):
            return
        try:
            self.chunks.put_nowait(chunk)
        except Full:
            try:
                self.chunks.get_nowait()
            except Empty:
                pass
            try:
                self.chunks.put_nowait(chunk)
            except Full:
                pass

    def _flush_single_samples(self):
        """Move a completed fixed-size sample block to the bounded queue."""
        if self._single_count:
            self.push(self._single_samples[:self._single_count])
            self._single_count = 0

    def sample(self, left, right):
        """Buffer single-sample callbacks without per-sample allocations."""
        self._single_samples[self._single_count] = (left, right)
        self._single_count += 1
        if self._single_count == SAMPLE_BLOCK_FRAMES:
            self._flush_single_samples()

    def batch(self, pointer, frames):
        # Preserve chronology if a core switches from single to batch mode.
        self._flush_single_samples()
        count = int(frames)
        if count < 0 or count > MAX_AUDIO_BATCH_FRAMES:
            # A malformed native length must not allocate a huge buffer or
            # read beyond the memory owned by the core.
            return 0
        if pointer and count:
            samples = np.ctypeslib.as_array(
                C.cast(pointer, C.POINTER(C.c_int16)), shape=(count * 2,)
            )
            self.push(samples.reshape(-1, 2))
        return count

    def callback(self, outdata, frames, time_info, status):
        """Fill every output frame, including silence during underruns."""
        outdata.fill(0)
        written = 0
        while written < frames:
            if self.position >= len(self.pending):
                try:
                    self.pending = self.chunks.get_nowait()
                except Empty:
                    break
                self.position = 0
            count = min(frames - written, len(self.pending) - self.position)
            outdata[written:written + count] = self.pending[
                self.position:self.position + count
            ]
            written += count
            self.position += count

    def start(self, sample_rate):
        self.output_error = None
        self.output_active = False
        if not (8_000 <= sample_rate <= 192_000):
            self.output_error = "Emulator reported an invalid sample rate"
            return
        if sd is None:
            self.output_error = "PortAudio or the audio backend is unavailable"
            print("Audio unavailable: " + self.output_error, file=sys.stderr)
            return

        source = int(round(sample_rate))
        # Prefer the actual output device's existing sample rate for unusual
        # Libretro values (notably 131072 Hz from GB/GBC). If unavailable,
        # 48000 is widely supported; only fall back if native rate fails.
        try:
            device = sd.query_devices(kind="output")
            preferred = int(round(float(device["default_samplerate"])))
        except (AttributeError, KeyError, IndexError, TypeError, ValueError):
            preferred = 48000
        if preferred not in NORMAL_DEVICE_RATES:
            preferred = 48000
        primary = source if source in NORMAL_DEVICE_RATES else preferred
        attempts = (primary,) if primary == preferred else (primary, preferred)
        error = None
        for rate in attempts:
            candidate = None
            try:
                candidate = sd.OutputStream(
                    samplerate=rate, channels=2, dtype="int16",
                    blocksize=1024, callback=self.callback,
                )
                candidate.start()
                self.stream = candidate
                self.output_active = True
                self.source_sample_rate = source
                self.output_sample_rate = rate
                if rate != source:
                    self._resample_step = float(sample_rate) / rate
                    self._resample_next = 0.0
                    self._resample_consumed = 0
                    self._resample_tail = None
                else:
                    self._resample_step = None
                return
            except Exception as exc:
                error = exc
                if candidate is not None:
                    try:
                        candidate.close()
                    except Exception:
                        pass
        self.output_error = "No usable audio output device: " + str(error)[:110]
        print("Audio output unavailable: " + str(error), file=sys.stderr)
        self.close()

    def close(self):
        self._flush_single_samples()
        self.output_active = False
        stream, self.stream = self.stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception as exc:
                print(f"Could not close audio output: {exc}", file=sys.stderr)
