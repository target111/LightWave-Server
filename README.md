# LightWave-Server

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

| Variable      | Default    | Description                              |
| ------------- | ---------- | ---------------------------------------- |
| `LED_COUNT`   | `300`      | Number of LEDs on the strip              |
| `LED_PIN`     | `D18`      | GPIO pin connected to the data line      |
| `LED_BACKEND` | `neopixel` | `neopixel` (hardware) or `mock` (dev)    |

## Running

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

Interactive API docs: `http://<host>:8000/docs`

## API

| Method | Path                    | Description                            |
| ------ | ----------------------- | -------------------------------------- |
| GET    | `/presets`              | List available effects                 |
| GET    | `/presets/running`      | Currently running effect               |
| GET    | `/presets/{name}`       | Effect description and options         |
| POST   | `/presets/start`        | Start an effect                        |
| POST   | `/presets/stop`         | Stop the running effect (fades out)    |
| POST   | `/leds/color/set`       | Set a static color                     |
| POST   | `/leds/color/brightness`| Set global brightness (0.0–1.0)        |
| POST   | `/leds/color/clear`     | Turn all LEDs off                      |

```bash
# Start an effect with custom options
curl -X POST http://localhost:8000/presets/start \
  -H "Content-Type: application/json" \
  -d '{"preset_name": "RainbowCycle", "args": {"speed": 2.5}}'

# Set a static color
curl -X POST http://localhost:8000/leds/color/set \
  -H "Content-Type: application/json" \
  -d '{"color": "#FF0000"}'
```

## Music visualizer

The `MusicVisualizer` effect listens for FFT data over UDP (default port
5555): one packet per frame containing little-endian float32 bins in the
0.0–1.0 range. When packets stop arriving it fades back to an ambient wave.

`music_client.py` is an early standalone client that captures system audio
via PipeWire/PulseAudio and streams the FFT (requires `numpy`). The
`ambilight*.py` scripts are early clients as well; a Rust client is in
development to replace them. None of their dependencies are part of the
server install.

## Writing an effect

Drop a class into `lib/effects/` — it is discovered automatically. Options
declared in `CONFIG_SCHEMA` are validated, coerced, and set as attributes.

```python
from lib.effects.base import EffectBase


class Blink(EffectBase):
    """Shows up as the effect description in the API."""

    CONFIG_SCHEMA = [
        {
            "name": "color",
            "type": "color",  # int | float | color
            "default": (255, 0, 0),
            "description": "Blink color",
        },
    ]

    color: tuple[int, int, int]

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)
        self.elapsed = 0.0

    def tick(self, dt: float):
        # Called in a 60 FPS loop; dt is the elapsed time in seconds.
        self.elapsed += dt
        on = int(self.elapsed) % 2 == 0
        self.led.set_color(self.color if on else (0, 0, 0))
```

## Development

```bash
uv run pytest                 # tests (uses the mock backend)
uv run ruff check lib tests   # lint
uv run pyright lib tests      # type check
```

## License

MIT — see [LICENSE](LICENSE).
