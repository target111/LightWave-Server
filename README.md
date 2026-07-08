<div align="center">
<img src="./.github/logo.svg" width="200" height="200" alt="LightWave logo" />

# LightWave-Server

</div>

HTTP API for controlling ws281x (NeoPixel) LED strips, built with FastAPI.
Runs on a Raspberry Pi; a mock backend allows development on any machine.

## Setup

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync               # server only
uv sync --extra pi    # on the Pi (adds blinka/neopixel)
uv sync --extra dev   # tests, lint, type checking
```

## Configuration

Set via environment variables:

| Variable       | Default        | Description                             |
| -------------- | -------------- | --------------------------------------- |
| `LED_COUNT`    | `300`          | Number of LEDs on the strip             |
| `LED_PIN`      | `D18`          | GPIO pin connected to the data line     |
| `LED_BACKEND`  | `neopixel`     | `neopixel` (hardware) or `mock` (dev)   |
| `PRESETS_FILE` | `presets.json` | Where user presets are persisted        |

## Running

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

Interactive API docs: `http://<host>:8000/docs`

## API

| Method | Path                    | Description                            |
| ------ | ----------------------- | -------------------------------------- |
| GET    | `/effects`              | List available effects                 |
| GET    | `/effects/running`      | Currently running effect               |
| GET    | `/effects/{name}`       | Effect description and options         |
| POST   | `/effects/start`        | Start an effect                        |
| POST   | `/effects/stop`         | Stop the running effect (fades out)    |
| GET    | `/presets`              | List saved presets                     |
| GET    | `/presets/{name}`       | One saved preset                       |
| PUT    | `/presets/{name}`       | Create or update a preset              |
| DELETE | `/presets/{name}`       | Delete a preset                        |
| POST   | `/presets/{name}/start` | Start the preset's effect              |
| GET    | `/leds`                 | Current pixels and brightness          |
| POST   | `/leds/color/set`       | Set a static color                     |
| POST   | `/leds/color/clear`     | Turn all LEDs off                      |
| POST   | `/leds/brightness`      | Set global brightness (0.0–1.0)        |

A *preset* is a saved configuration of an effect — a name, the effect it
runs, and the option values to run it with. Presets live in one JSON file
on the server (`PRESETS_FILE`), so every client sees the same list. Preset
names must not collide with effect names.

```bash
# Start an effect with custom options
curl -X POST http://localhost:8000/effects/start \
  -H "Content-Type: application/json" \
  -d '{"effect_name": "RainbowCycle", "args": {"speed": 2.5}}'

# Save those options as a preset, then start it by name
curl -X PUT http://localhost:8000/presets/party \
  -H "Content-Type: application/json" \
  -d '{"effect": "RainbowCycle", "args": {"speed": 2.5}, "description": "fast rainbow"}'
curl -X POST http://localhost:8000/presets/party/start

# Set a static color
curl -X POST http://localhost:8000/leds/color/set \
  -H "Content-Type: application/json" \
  -d '{"color": "#FF0000"}'
```

## Writing an effect

Drop a class into `lib/effects/library/` — it is discovered automatically
(files starting with `_` are skipped; copy `_template.py` to get started).

```python
from lib.effects.base import Color, EffectBase, option


class Blink(EffectBase):
    """Shows up as the effect description in the API."""

    color: Color = option((255, 0, 0), "Blink color")
    period: float = option(1.0, "Seconds per on/off phase", min=0.05)

    def setup(self):
        self.elapsed = 0.0

    def tick(self, dt: float):
        # Called in a 60 FPS loop; dt is the elapsed time in seconds.
        self.elapsed += dt
        on = int(self.elapsed / self.period) % 2 == 0
        self.fill(self.color if on else (0, 0, 0))
```

- **Options** are one `option(default, description, min=..., max=...)` line
  each; the type comes from the annotation (`int`, `float`, `bool`, `Color`).
  API values are coerced, bounds-checked, and set as attributes, so the
  effect just reads `self.period`.
- **State** goes in `setup()` — no `__init__` boilerplate.
- **Drawing** means writing `(r, g, b)` tuples into `self.pixels` (or
  `self.fill(color)` / `self.clear()`); the loop pushes the buffer to the
  hardware after every `tick()`. The buffer persists between frames.
- **Helpers**: `lib.effects.colors` (`hsv`, `lerp`, `scale`, `wheel`,
  `Gradient`) and `lib.effects.anim` (`fade_factor`, `wrap`, `Spawner`,
  `FadeBuffer`) cover the common color math and motion patterns.

Option conventions: times in seconds, sizes in pixels, rates per second,
probabilities 0.0–1.0. Unitless knobs (speed, density, …) are multipliers
where `1.0` is the designed look; keep the tuned base value inside the
effect as a named constant.

Preview any effect in the terminal, no hardware needed:

```bash
uv run python -m lib.effects.preview            # list effects
uv run python -m lib.effects.preview Fire cooling=1.3
```

## Development

```bash
uv run pytest                 # tests (uses the mock backend)
uv run ruff check lib tests   # lint
uv run pyright lib tests      # type check
```

## License

MIT — see [LICENSE](LICENSE).
