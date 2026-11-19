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
MAX_QUEUE_CHUNK_FRAMES = 4096
NORMAL_DEVICE_RATES = frozenset((
    8000, 11025, 16000, 22050, 32000, 44100, 48000, 88200, 96000,
))


def _audio_diagnostic(message):
    """Best-effort fixed text; a closed stderr must not stop emulation."""
    try:
        print(message, file=sys.stderr)
    except Exception:
        # Frozen GUI launchers, closed pipes and sandboxed audio sessions may
        # have no writable stderr. Audio failure is already recorded in the
        # app status; the optional diagnostic must never become fatal.
        pass


class AudioSink:
    """Keep the core's audio callbacks independent from the output device."""

    def __init__(self):
        self.chunks = Queue(maxsize=32)
        self.pending = np.empty((0, 2), dtype=np.int16)
        self.position = 0
        self.stream = None
        self.output_error = None
        self.output_active = False
        # Lifetime evidence survives close() for the final GameCube report.
        # "No underflows" without a stream is not evidence of audible audio.
        self.output_ever_started = False
        self.source_sample_rate = None
        self.output_sample_rate = None
        # Bounded-size, aggregate diagnostics only. PCM generation is not
        # proof that PortAudio consumed a block or a speaker played sound.
        # No samples, filenames, devices or per-callback timestamps retained.
        self.output_callback_calls = 0
        self.output_callback_requested_frames = 0
        self.output_underrun_frames = 0
        self.output_device_underflow_callbacks = 0
        self.queue_dropped_frames = 0
        # AudioSink by itself is a transparent PCM sink for native testing.
        # CoreSession explicitly applies the user's 35% default or saved gain
        # before playback, leaving existing raw audio contracts unchanged.
        self._volume = 1.0
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

    def _enqueue_bounded(self, chunk):
        """A malicious or broken core cannot retain an enormous queued batch."""
        for start in range(0, len(chunk), MAX_QUEUE_CHUNK_FRAMES):
            part = chunk[start:start + MAX_QUEUE_CHUNK_FRAMES].copy()
            try:
                self.chunks.put_nowait(part)
            except Full:
                try:
                    dropped = self.chunks.get_nowait()
                except Empty:
                    pass
                else:
                    self.queue_dropped_frames += len(dropped)
                try:
                    self.chunks.put_nowait(part)
                except Full:
                    # Another producer can race for space after eviction.
                    # Count this chunk too: its PCM was never delivered.
                    self.queue_dropped_frames += len(part)

    def push(self, samples):
        if not len(samples):
            return
        chunk = np.asarray(samples, dtype=np.int16).reshape(-1, 2)
        for start in range(0, len(chunk), RESAMPLE_INPUT_CHUNK):
            part = chunk[start:start + RESAMPLE_INPUT_CHUNK].copy()
            if self._resample_step is not None:
                part = self._resample(part)
            if len(part):
                self._enqueue_bounded(part)

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

    def set_volume(self, level):
        """Bounded output gain, read atomically by the audio callback."""
        try:
            gain = float(level)
        except (TypeError, ValueError, OverflowError):
            gain = 0.35
        if not np.isfinite(gain):
            gain = 0.35
        self._volume = max(0.0, min(1.0, gain))

    def callback(self, outdata, frames, time_info, status):
        """Fill every output frame, including silence during underruns."""
        # PortAudio invokes this from its audio thread. Track only aggregate
        # counts; do not record private audio or equate callback activity
        # with proof of audible playback on physical speakers.
        self.output_callback_calls += 1
        self.output_callback_requested_frames += frames
        # PortAudio's output-underflow flag detects device scheduling
        # problems independently of our own empty PCM queue. In particular,
        # a healthy queue can still underrun at the speaker interface.
        # Always initialize the speaker buffer before observing optional
        # third-party PortAudio status objects. A malformed status getter
        # must not crash the realtime callback or leave old output samples.
        outdata.fill(0)
        try:
            if status is not None and getattr(status, "output_underflow", False):
                self.output_device_underflow_callbacks += 1
        except Exception:
            # Only the optional device-underflow counter is unavailable.
            # Continue delivering the same PCM; never expose driver text.
            pass
        written = 0
        while written < frames:
            if self.position >= len(self.pending):
                try:
                    self.pending = self.chunks.get_nowait()
                except Empty:
                    break
                self.position = 0
            count = min(frames - written, len(self.pending) - self.position)
            gain = self._volume
            if gain >= 1.0:
                outdata[written:written + count] = self.pending[
                    self.position:self.position + count
                ]
            elif gain > 0.0:
                # Scale only the current bounded block; never resample again
                # or risk uint/int16 overflow when applying the gain.
                output = self.pending[self.position:self.position + count]
                outdata[written:written + count] = np.rint(
                    output.astype(np.float32) * gain
                ).astype(np.int16)
            # Mute leaves the already-zeroed output untouched, but the
            # queue is still consumed so unmuting never replays old audio.
            written += count
            self.position += count
        self.output_underrun_frames += max(0, frames - written)

    def delivery_snapshot(self):
        """Aggregate callback/queue telemetry, not verified speaker output."""
        return {
            "audio_output_callback_calls": self.output_callback_calls,
            "audio_output_requested_frames": self.output_callback_requested_frames,
            "audio_output_underrun_frames": self.output_underrun_frames,
            "audio_output_device_underflow_callbacks": (
                self.output_device_underflow_callbacks
            ),
            "audio_queue_dropped_frames": self.queue_dropped_frames,
        }

    def start(self, sample_rate):
        self.output_error = None
        self.output_active = False
        # Libretro's AVInfo supplies a floating-point native sample rate.
        # A broken core can report NaN/Inf or an out-of-range rate. Merely
        # comparing a NaN against numeric bounds returns False on both sides;
        # round(NaN) then raises and can abort game startup. Fail silently
        # and visibly before calling PortAudio or touching any device.
        try:
            if (isinstance(sample_rate, (bool, np.bool_))
                    or not isinstance(sample_rate, (
                        int, float, np.integer, np.floating
                    ))):
                raise ValueError("not a numeric sample rate")
            numeric_rate = float(sample_rate)
            if (not np.isfinite(numeric_rate)
                    or not 8_000 <= numeric_rate <= 192_000):
                raise ValueError("invalid numeric sample rate")
            source = int(round(numeric_rate))
        except (TypeError, ValueError, OverflowError):
            self.output_error = "Emulator reported an invalid sample rate"
            return
        if sd is None:
            self.output_error = "PortAudio or the audio backend is unavailable"
            _audio_diagnostic("Audio unavailable: " + self.output_error)
            return

        # Prefer the actual output device's existing sample rate for unusual
        # Libretro values (notably 131072 Hz from GB/GBC). If unavailable,
        # 48000 is widely supported; only fall back if native rate fails.
        try:
            device = sd.query_devices(kind="output")
            preferred = int(round(float(device["default_samplerate"])))
        except Exception:
            # sounddevice.PortAudioError is NOT an OSError or ValueError.
            # Headless CI, unplugged speakers and sessions with no default
            # device all raise here. Never let audio discovery kill a game.
            # The fallback stream will report a device failure separately.
            preferred = 48000
        if preferred not in NORMAL_DEVICE_RATES:
            preferred = 48000
        primary = source if source in NORMAL_DEVICE_RATES else preferred
        # Device metadata can be stale after HDMI/USB audio switches. Some
        # drivers also reject their advertised default. Try both standard
        # stereo rates as final fallbacks before giving up on real output.
        # Keep this finite and ordered: never create more than four streams.
        attempts = tuple(dict.fromkeys((primary, preferred, 48000, 44100)))
        # Libretro may emit samples during retro_init/load_game BEFORE audio
        # starts. Flush the partial single-sample block into the source-rate
        # queue too; otherwise it misses startup resampling.
        self._flush_single_samples()
        error = None
        for rate in attempts:
            candidate = None
            # A driver can invoke an output callback from start() and then
            # reject the stream. Snapshot ALL source-rate playback state,
            # not only queued PCM: an attempted callback advances pending
            # and position even if native stream startup later fails.
            source_chunks = self.chunks
            source_pending, source_position = self.pending, self.position
            prior_dropped = self.queue_dropped_frames
            prior_callbacks = (
                self.output_callback_calls,
                self.output_callback_requested_frames,
                self.output_underrun_frames,
                self.output_device_underflow_callbacks,
            )
            try:
                candidate = sd.OutputStream(
                    samplerate=rate, channels=2, dtype="int16",
                    blocksize=1024, callback=self.callback,
                )
                # Every candidate (including the unchanged native rate)
                # reads a separate bounded queue. A rejected stream may
                # consume its copy, but never the source needed for retry.
                self.chunks = Queue(maxsize=32)
                self.pending = np.empty((0, 2), dtype=np.int16)
                self.position = 0
                self._resample_step = (
                    numeric_rate / rate if rate != source else None
                )
                self._resample_next = 0.0
                self._resample_consumed = 0
                self._resample_tail = None
                if source_position < len(source_pending):
                    self.push(source_pending[source_position:])
                for old in list(source_chunks.queue):
                    self.push(old)
                # The first PortAudio callback may be synchronous. The
                # correct resampled PCM and phase must already be ready.
                candidate.start()
                self.stream = candidate
                self.output_active = True
                self.output_ever_started = True
                self.source_sample_rate = source
                self.output_sample_rate = rate
                return
            except Exception as exc:
                error = exc
                if candidate is not None:
                    try:
                        candidate.close()
                    except Exception:
                        pass
                # Never leak played, partially consumed or differently
                # resampled PCM into the next candidate. Its stream may
                # have started a callback just before reporting failure.
                self.chunks = source_chunks
                self.pending, self.position = source_pending, source_position
                self.queue_dropped_frames = prior_dropped
                (
                    self.output_callback_calls,
                    self.output_callback_requested_frames,
                    self.output_underrun_frames,
                    self.output_device_underflow_callbacks,
                ) = prior_callbacks
                self._resample_step = None
                self._resample_next = 0.0
                self._resample_consumed = 0
                self._resample_tail = None
        # OS PortAudio failures may include a device name, home directory,
        # USB identifier or driver path. The UI, stderr and diagnostic
        # reports must never forward that untrusted platform exception text.
        # Retain just the fixed error class for actionable troubleshooting.
        reason = type(error).__name__ if error is not None else "UnknownError"
        self.output_error = "No usable audio output device (" + reason + ")"
        _audio_diagnostic("Audio output unavailable (" + reason + ")")
        self.close()

    def close(self):
        self._flush_single_samples()
        self.output_active = False
        stream, self.stream = self.stream, None
        if stream is not None:
            try:
                stream.stop()
            except Exception as exc:
                # stop() can fail after a USB output is unplugged. Still
                # attempt close() so the host releases its device handle.
                _audio_diagnostic(
                    "Could not stop audio output (" + type(exc).__name__ + ")"
                )
            try:
                stream.close()
            except Exception as exc:
                # A separate close failure must not block core shutdown or
                # copy device names/paths from the platform exception.
                _audio_diagnostic(
                    "Could not close audio output (" + type(exc).__name__ + ")"
                )
