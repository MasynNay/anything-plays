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


class AudioSink:
    """Keep the core's audio callbacks independent from the output device."""

    def __init__(self):
        self.chunks = Queue(maxsize=32)
        self.pending = np.empty((0, 2), dtype=np.int16)
        self.position = 0
        self.stream = None
        # Some Libretro cores send individual samples instead of batches.
        # Avoid creating 44,100 NumPy arrays / queue entries per second.
        self._single_samples = np.empty(
            (SAMPLE_BLOCK_FRAMES, 2), dtype=np.int16
        )
        self._single_count = 0

    def push(self, samples):
        if not len(samples):
            return
        chunk = np.asarray(samples, dtype=np.int16).reshape(-1, 2).copy()
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
        if sd is None:
            print("Audio unavailable: sounddevice not installed", file=sys.stderr)
            return
        if not (8_000 <= sample_rate <= 192_000):
            return
        try:
            self.stream = sd.OutputStream(
                samplerate=int(round(sample_rate)), channels=2,
                dtype="int16", blocksize=1024, callback=self.callback,
            )
            self.stream.start()
        except Exception as exc:
            print(f"Audio output unavailable: {exc}", file=sys.stderr)
            self.close()

    def close(self):
        self._flush_single_samples()
        stream, self.stream = self.stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception as exc:
                print(f"Could not close audio output: {exc}", file=sys.stderr)
