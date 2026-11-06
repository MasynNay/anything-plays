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


class AudioSink:
    """Keep the core's audio callbacks independent from the output device."""

    def __init__(self):
        self.chunks = Queue(maxsize=32)
        self.pending = np.empty((0, 2), dtype=np.int16)
        self.position = 0
        self.stream = None

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

    def sample(self, left, right):
        self.push(np.array([[left, right]], dtype=np.int16))

    def batch(self, pointer, frames):
        if pointer and frames:
            samples = np.ctypeslib.as_array(
                C.cast(pointer, C.POINTER(C.c_int16)), shape=(int(frames) * 2,)
            )
            self.push(samples.reshape(-1, 2))
        return frames

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
        stream, self.stream = self.stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception as exc:
                print(f"Could not close audio output: {exc}", file=sys.stderr)
