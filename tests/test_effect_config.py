"""Effects resolve their options from CONFIG_SCHEMA in EffectBase:
defaults applied, values coerced, attributes set."""

import pytest

from lib.effects.base import EffectBase, fade_factor
from lib.effects.candy_cane import CandyCane
from lib.effects.registry import EffectRegistry


def test_defaults_become_attributes(led):
    effect = CandyCane(led)
    assert effect.speed == 1.0
    assert effect.stripe_width == 5
    assert effect.color1 == (255, 0, 0)


def test_overrides_are_coerced(led):
    # JSON bodies deliver colors as lists and numbers as the wrong type
    effect = CandyCane(led, stripe_width="7", color1=[0, 128, 255])
    assert effect.stripe_width == 7
    assert effect.color1 == (0, 128, 255)


def test_bad_value_raises(led):
    with pytest.raises(ValueError, match="stripe_width"):
        CandyCane(led, stripe_width="not a number")


def test_unknown_option_warns_but_works(led, caplog):
    effect = CandyCane(led, nonsense=1)
    assert effect.speed == 1.0
    assert "nonsense" in caplog.text


# Effects that bind OS resources in __init__; port=0 picks a free port
# instead of the real one.
EXTRA_ARGS = {
    "MusicVisualizer": {"port": 0},
    "Ambilight": {"port": 0},
}


def test_every_registered_effect_constructs_and_ticks(led):
    registry = EffectRegistry()
    names = registry.names()
    assert len(names) >= 12

    for name in names:
        effect = registry.get(name)(led, **EXTRA_ARGS.get(name, {}))
        try:
            for _ in range(3):
                effect.tick(1 / 60)
        finally:
            effect.teardown()


def test_schema_defaults_match_resolved_config(led):
    """Every schema entry must produce a same-named attribute."""
    registry = EffectRegistry()
    for name in registry.names():
        cls = registry.get(name)
        effect = cls(led, **EXTRA_ARGS.get(name, {}))
        try:
            for spec in cls.CONFIG_SCHEMA:
                assert hasattr(effect, spec["name"]), (
                    f"{name} missing option attribute {spec['name']!r}"
                )
        finally:
            effect.teardown()


def test_fade_factor_reaches_residual_after_fade_time():
    value = 1.0
    for _ in range(60):
        value *= fade_factor(1 / 60, fade_time=1.0)
    assert value == pytest.approx(0.05)
    assert fade_factor(1 / 60, fade_time=0.0) == 0.0


def test_animation_speed_is_frame_rate_independent(led):
    """One simulated second advances the same amount at 30 and 120 FPS."""
    slow = CandyCane(led)
    fast = CandyCane(led)
    for _ in range(30):
        slow.tick(1 / 30)
    for _ in range(120):
        fast.tick(1 / 120)
    assert slow.offset == pytest.approx(fast.offset)


def test_option_clashing_with_thread_attribute_is_rejected(led):
    class BadEffect(EffectBase):
        CONFIG_SCHEMA = [
            {
                "name": "name",
                "type": "float",
                "default": 1.0,
                "description": "clashes with threading.Thread.name",
            }
        ]

        def tick(self, dt):
            pass

    with pytest.raises(ValueError, match="clashes"):
        BadEffect(led)
