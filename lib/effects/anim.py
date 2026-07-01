"""Timing and motion primitives shared by effects. Everything here takes
`dt` in seconds so animations stay frame-rate independent."""


def fade_factor(dt: float, fade_time: float, residual: float = 0.05) -> float:
    """Per-tick multiplier so an exponentially decaying value reaches
    `residual` of its starting point after `fade_time` seconds."""
    if fade_time <= 0:
        return 0.0
    return residual ** (dt / fade_time)


def wrap(value: float, period: float) -> float:
    """Wrap a phase accumulator into [0, period)."""
    return value % period


class Spawner:
    """Turn an events-per-second rate into a per-tick spawn count.

    Accumulates fractional spawns across frames, so — unlike
    `random.random() < rate * dt` — rates above one event per frame and
    slow frames both produce the correct number of events.

        spawner = Spawner(rate=2.5)
        for _ in range(spawner.poll(dt)):
            spawn_one()
    """

    def __init__(self, rate: float = 0.0):
        self.rate = rate
        self._accum = 0.0

    def poll(self, dt: float, rate: float | None = None) -> int:
        """Number of events due this tick. `rate` overrides the stored
        rate for effects that modulate it every frame."""
        self._accum += (self.rate if rate is None else rate) * dt
        count = int(self._accum)
        self._accum -= count
        return count

    def reset(self) -> None:
        """Drop any accumulated fraction (e.g. when the source goes quiet)."""
        self._accum = 0.0


class FadeBuffer:
    """Per-pixel 0.0-1.0 intensities that decay exponentially toward zero.

        trail = FadeBuffer(n, fade_time=1.6)
        trail.decay(dt)
        trail[head] = 1.0
        for i, v in enumerate(trail):
            ...
    """

    def __init__(self, n: int, fade_time: float):
        self.values = [0.0] * n
        self.fade_time = fade_time

    def decay(self, dt: float) -> None:
        factor = fade_factor(dt, self.fade_time)
        self.values = [v * factor for v in self.values]

    def __getitem__(self, index: int) -> float:
        return self.values[index]

    def __setitem__(self, index: int, value: float) -> None:
        self.values[index] = value

    def __len__(self) -> int:
        return len(self.values)

    def __iter__(self):
        return iter(self.values)
