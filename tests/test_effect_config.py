"""Effects resolve their options from CONFIG_SCHEMA in EffectBase:
defaults applied, values coerced, attributes set."""

import pytest

from lib.effects.base import EffectBase
from lib.effects.candy_cane import CandyCane
from lib.effects.registry import EffectRegistry


def test_defaults_become_attributes(led):
    effect = CandyCane(led)
    assert effect.speed == 0.33
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
    assert effect.speed == 0.33
    assert "nonsense" in caplog.text


def test_every_registered_effect_constructs_and_ticks(led):
    registry = EffectRegistry()
    names = registry.names()
    assert len(names) >= 12

    for name in names:
        # port=0 keeps MusicVisualizer off the real port; other effects
        # just log it as an unknown option and ignore it.
        effect = registry.get(name)(led, port=0)
        try:
            for _ in range(3):
                effect.tick()
        finally:
            effect.teardown()


def test_schema_defaults_match_resolved_config(led):
    """Every schema entry must produce a same-named attribute."""
    registry = EffectRegistry()
    for name in registry.names():
        cls = registry.get(name)
        effect = cls(led, port=0)
        try:
            for spec in cls.CONFIG_SCHEMA:
                assert hasattr(effect, spec["name"]), (
                    f"{name} missing option attribute {spec['name']!r}"
                )
        finally:
            effect.teardown()


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

        def tick(self):
            pass

    with pytest.raises(ValueError, match="clashes"):
        BadEffect(led)
