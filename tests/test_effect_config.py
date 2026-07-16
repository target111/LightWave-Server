"""Effects declare options with option(); EffectBase resolves them:
defaults applied, values coerced, bounds checked, attributes set."""

import pytest

from lib.effects.base import EffectBase, option
from lib.effects.library.candy_cane import CandyCane
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


def test_out_of_range_value_raises(led):
    # stripe_width=0 used to reach tick() and divide by zero
    with pytest.raises(ValueError, match="stripe_width"):
        CandyCane(led, stripe_width=0)


def test_bounds_appear_in_schema():
    spec = next(
        s for s in CandyCane.CONFIG_SCHEMA if s["name"] == "stripe_width"
    )
    assert spec["type"] == "int"
    assert spec["min"] == 1


def test_unknown_option_warns_but_works(led, caplog):
    effect = CandyCane(led, nonsense=1)
    assert effect.speed == 1.0
    assert "nonsense" in caplog.text


def _test_overrides(cls) -> dict:
    """Effects with a `port` option bind a UDP socket in setup();
    port=0 picks a free port instead of the real one."""
    has_port = any(spec["name"] == "port" for spec in cls.CONFIG_SCHEMA)
    return {"port": 0} if has_port else {}


def test_every_registered_effect_constructs_and_ticks(led):
    registry = EffectRegistry()
    names = registry.names()
    assert len(names) >= 12

    for name in names:
        cls = registry.get(name)
        effect = cls(led, **_test_overrides(cls))
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
        effect = cls(led, **_test_overrides(cls))
        try:
            for spec in cls.CONFIG_SCHEMA:
                assert hasattr(effect, spec["name"]), (
                    f"{name} missing option attribute {spec['name']!r}"
                )
        finally:
            effect.teardown()


def test_tick_fills_frame_buffer(led, driver):
    """Effects draw into self.pixels; the run loop pushes the buffer."""
    effect = CandyCane(led)
    effect.tick(1 / 60)
    led.set_pixels(effect.pixels)
    assert driver.snapshot()[0] == (255, 0, 0)


def test_animation_speed_is_frame_rate_independent(led):
    """One simulated second advances the same amount at 30 and 120 FPS."""
    slow = CandyCane(led)
    fast = CandyCane(led)
    for _ in range(30):
        slow.tick(1 / 30)
    for _ in range(120):
        fast.tick(1 / 120)
    assert slow.offset == pytest.approx(fast.offset)


def test_name_defaults_to_class_name():
    class Plain(EffectBase):
        def tick(self, dt):
            pass

    assert Plain.NAME == "Plain"


def test_explicit_name_survives_and_is_not_inherited():
    class Renamed(EffectBase):
        # Simulates a class rename keeping its published API name.
        NAME = "OldName"

        def tick(self, dt):
            pass

    class Child(Renamed):
        pass

    assert Renamed.NAME == "OldName"
    # A subclass gets its own default instead of the parent's public name.
    assert Child.NAME == "Child"


def test_registry_keys_effects_by_public_name():
    registry = EffectRegistry()
    assert registry.get("CandyCane") is CandyCane
    assert CandyCane.NAME == "CandyCane"


def test_option_clashing_with_thread_attribute_is_rejected():
    with pytest.raises(ValueError, match="clashes"):

        class BadEffect(EffectBase):
            # The clash with threading.Thread.name is the point here
            name: float = option(  # pyright: ignore[reportIncompatibleVariableOverride]
                1.0, "clashes with threading.Thread.name"
            )

            def tick(self, dt):
                pass


def test_option_without_annotation_is_rejected():
    with pytest.raises(TypeError, match="annotation"):

        class BadEffect(EffectBase):
            speed = option(1.0, "missing the type annotation")

            def tick(self, dt):
                pass


def test_handwritten_config_schema_is_rejected():
    with pytest.raises(TypeError, match="CONFIG_SCHEMA"):

        class OldStyleEffect(EffectBase):
            CONFIG_SCHEMA = [
                {"name": "speed", "type": "float", "default": 1.0}
            ]

            def tick(self, dt):
                pass
