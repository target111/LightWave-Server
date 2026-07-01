"""Preview any registered effect in the terminal — no hardware needed.

    python -m lib.effects.preview                      # list effects
    python -m lib.effects.preview Fire                 # run with defaults
    python -m lib.effects.preview Fire cooling=1.3     # override options
    python -m lib.effects.preview CandyCane color1=255,80,0 --leds 40

Requires a terminal with 24-bit color support. Ctrl+C to exit.
"""

import argparse
import sys
import time

from lib.drivers.controller import LEDController
from lib.drivers.mock_driver import MockDriver
from lib.effects.registry import EffectRegistry


def _parse_option(pair: str) -> tuple[str, object]:
    name, sep, raw = pair.partition("=")
    if not sep or not name:
        raise SystemExit(f"expected name=value, got {pair!r}")
    if "," in raw:  # color: r,g,b
        return name, tuple(int(p) for p in raw.split(","))
    return name, raw  # strings are coerced by the option machinery


def _render(pixels) -> str:
    return "".join(f"\x1b[38;2;{r};{g};{b}m█" for r, g, b in pixels)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m lib.effects.preview",
        description="Render an effect as ANSI blocks using the mock driver.",
    )
    parser.add_argument("effect", nargs="?", help="Effect name; omit to list")
    parser.add_argument(
        "options", nargs="*", metavar="name=value", help="Option overrides"
    )
    parser.add_argument("--leds", type=int, default=60, help="Strip length")
    args = parser.parse_args(argv)

    registry = EffectRegistry()
    if not args.effect:
        for name in registry.names():
            print(f"{name}: {registry.describe(name)}")
        return 0

    if not registry.has(args.effect):
        print(f"Unknown effect {args.effect!r}. Available:", file=sys.stderr)
        print("  " + ", ".join(registry.names()), file=sys.stderr)
        return 1

    overrides = dict(_parse_option(pair) for pair in args.options)
    driver = MockDriver(args.leds)
    effect = registry.get(args.effect)(LEDController(driver), **overrides)

    # Drive tick() directly instead of starting the thread, mirroring the
    # run loop: tick, push the frame buffer, sleep off the frame budget.
    frame_time = 1.0 / effect.TARGET_FPS
    last = time.perf_counter()
    try:
        while True:
            loop_start = time.perf_counter()
            dt = min(loop_start - last, 3 * frame_time)
            last = loop_start
            effect.tick(dt)
            effect.led.set_pixels(effect.pixels)
            sys.stdout.write("\r" + _render(driver.snapshot()) + "\x1b[0m")
            sys.stdout.flush()
            wait = frame_time - (time.perf_counter() - loop_start)
            if wait > 0:
                time.sleep(wait)
    except (KeyboardInterrupt, BrokenPipeError):
        return 0
    finally:
        effect.teardown()
        try:
            sys.stdout.write("\x1b[0m\n")
        except BrokenPipeError:
            pass


if __name__ == "__main__":
    sys.exit(main())
