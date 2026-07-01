"""The shared color and animation primitives effects build on."""

import pytest

from lib.effects.anim import FadeBuffer, Spawner, fade_factor, wrap
from lib.effects.colors import Gradient, hsv, lerp, scale, wheel


def test_fade_factor_reaches_residual_after_fade_time():
    value = 1.0
    for _ in range(60):
        value *= fade_factor(1 / 60, fade_time=1.0)
    assert value == pytest.approx(0.05)
    assert fade_factor(1 / 60, fade_time=0.0) == 0.0


def test_wrap():
    assert wrap(257.5, 256) == pytest.approx(1.5)
    assert wrap(100.0, 256) == pytest.approx(100.0)


def test_spawner_rate_is_frame_rate_independent():
    slow, fast = Spawner(2.5), Spawner(2.5)
    slow_total = sum(slow.poll(1 / 30) for _ in range(30))
    fast_total = sum(fast.poll(1 / 120) for _ in range(120))
    assert slow_total == fast_total == 2


def test_spawner_handles_multiple_events_per_frame():
    # random.random() < rate*dt caps at 1 per frame; Spawner must not
    assert Spawner(120.0).poll(1 / 30) == 4


def test_spawner_rate_override_and_reset():
    spawner = Spawner()
    assert spawner.poll(1.0, rate=3.0) == 3
    spawner.poll(1.0, rate=0.5)
    spawner.reset()
    assert spawner.poll(1.0, rate=0.4) == 0  # fraction was dropped


def test_fade_buffer_decays_toward_zero():
    buffer = FadeBuffer(3, fade_time=1.0)
    buffer[1] = 1.0
    for _ in range(60):
        buffer.decay(1 / 60)
    assert buffer[0] == 0.0
    assert buffer[1] == pytest.approx(0.05)
    assert len(buffer) == 3
    assert list(buffer)[2] == 0.0


def test_gradient_endpoints_and_interpolation():
    heat = Gradient((0, 0, 0), (255, 0, 0), (255, 255, 0))
    assert heat.sample(0.0) == (0, 0, 0)
    assert heat.sample(0.5) == (255, 0, 0)
    assert heat.sample(1.0) == (255, 255, 0)
    assert heat.sample(0.25) == (127, 0, 0)
    assert heat.sample(2.0) == (255, 255, 0)  # clamped


def test_gradient_needs_two_stops():
    with pytest.raises(ValueError):
        Gradient((255, 0, 0))


def test_color_helpers():
    assert lerp((0, 0, 0), (255, 0, 0), 0.5) == (127, 0, 0)
    assert scale((100, 200, 50), 0.5) == (50, 100, 25)
    assert hsv(0.0, 1.0, 1.0) == (255, 0, 0)
    assert hsv(1.0, 1.0, 1.0) == (255, 0, 0)  # hue wraps
    assert wheel(0) == (0, 255, 0)
    assert wheel(256) == wheel(0)  # position wraps
