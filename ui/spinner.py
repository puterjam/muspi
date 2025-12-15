import time

class Spinner:
    def __init__(self, frames, interval):
        self._frames = tuple(frames)
        self._interval = interval
        self._pos = 0
        self._last = time.monotonic()

    def frame(self):
        now = time.monotonic()
        if now - self._last >= self._interval:
            self._pos = (self._pos + 1) % len(self._frames)
            self._last = now
        return self._frames[self._pos]