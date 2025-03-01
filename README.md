<div align="center">
<h1 align="center">
<img src="https://raw.githubusercontent.com/PKief/vscode-material-icon-theme/ec559a9f6bfd399b82bb44393651661b08aaf7ba/icons/folder-markdown-open.svg" width="100" />
<br>LightWave-Server
</h1>
<h3>◦ LightWave: An HTTP API server for controlling ws281x LED lights. </h3>

<p align="center">
<img src="https://img.shields.io/badge/Python-3776AB.svg?style&logo=Python&logoColor=white" alt="Python" />
</p>
<img src="https://img.shields.io/github/languages/top/target111/LightWave-Server?style&color=81a1c1" alt="GitHub top language" />
<img src="https://img.shields.io/github/languages/code-size/target111/LightWave-Server?style&color=a3be8c&" alt="GitHub code size in bytes" />
<img src="https://img.shields.io/github/commit-activity/m/target111/LightWave-Server?style&color=bf616a" alt="GitHub commit activity" />
<img src="https://img.shields.io/github/license/target111/LightWave-Server?style&color=b48ead" alt="GitHub license" />
</div>

---

## 📒 Table of Contents
- [📒 Table of Contents](#-table-of-contents)
- [📍 Overview](#-overview)
- [⚙️ Features](#️-features)
- [📂 Project Structure](#-project-structure)
- [🚀 Getting Started](#-getting-started)
  - [✔️ Prerequisites](#️-prerequisites)
  - [📦 Installation](#-installation)
  - [🎮 Running the Server](#-running-the-server)
  - [🌈 Using Effects](#-using-effects)
  - [🔧 Configuration](#-configuration)
- [🧩 API Endpoints](#-api-endpoints)
- [✨ Creating Custom Effects](#-creating-custom-effects)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

---

## 📍 Overview

LightWave-Server is a modern Python-based server for controlling WS281X LED lights (NeoPixels) via a RESTful HTTP API. It provides an extensive framework for creating, managing, and running dynamic LED effects with customizable parameters. The project is designed with flexibility in mind, allowing both direct color control and complex animated effects.

The new version (2.0.0) has been completely refactored with a proper package structure, improved configuration system, comprehensive error handling, proper logging, and extensive documentation.

---

## ⚙️ Features

| Feature                | Description                                                                                                                                                                                                                |
|------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **⚙️ Architecture**     | Clean and modular architecture with proper separation of concerns between LED control, effects system, configuration, and API.                                   |
| **🎨 Effect System**    | Flexible effect system with parameterization support, dynamic loading, and automatic registration.                                                               |
| **⚡️ Performance**      | Optimized frame rate management and efficient LED control with hardware or simulated controls.                                                                  |
| **🔧 Configuration**    | Environment variable-based configuration with sensible defaults and typed settings classes.                                                                     |
| **📚 API**              | Well-documented FastAPI-based REST API with comprehensive validation and error handling.                                                                        |
| **🔌 Extensibility**    | Easy to extend with new effects by adding a single Python file.                                                                                                |
| **🏭 Mock Mode**        | Support for a mock mode to run without hardware for development and testing.                                                                                   |
| **🔍 Logging**          | Comprehensive logging with configurable log levels.                                                                                                            |

---

## 📂 Project Structure

The codebase is organized into a proper Python package with the following structure:

```
lightwave-server/
├── lightwave/               # Main package
│   ├── __init__.py          # Package initialization
│   ├── __main__.py          # Entry point for CLI usage
│   ├── api/                 # API module
│   │   ├── __init__.py
│   │   ├── models.py        # Pydantic models for API
│   │   └── server.py        # FastAPI server implementation
│   ├── config/              # Configuration module
│   │   ├── __init__.py
│   │   └── settings.py      # Configuration classes
│   ├── controller/          # LED controller module
│   │   ├── __init__.py
│   │   ├── led.py           # LED controller classes
│   │   └── manager.py       # LED manager
│   ├── effects/             # Effects module
│   │   ├── __init__.py
│   │   ├── base.py          # Base effect class
│   │   ├── registry.py      # Effect registry
│   │   ├── rainbow.py       # Rainbow effect
│   │   ├── pulse.py         # Pulse effect
│   │   └── twinkle.py       # Twinkle effect
│   └── utils/               # Utilities
│       ├── __init__.py
│       ├── color.py         # Color utilities
│       └── logging.py       # Logging utilities
├── main.py                  # Simple entry point for backward compatibility
├── setup.py                 # Package setup
├── requirements.txt         # Dependencies
├── LICENSE                  # License file
└── README.md                # This file
```

---

## 🚀 Getting Started

### ✔️ Prerequisites

Before you begin, ensure that you have the following prerequisites installed:
- Python 3.9 or higher
- Raspberry Pi or similar device with GPIO pins (for hardware mode)
- WS281X LED strip connected to the GPIO pins

### 📦 Installation

1. Clone the LightWave-Server repository:
```sh
git clone https://github.com/target111/LightWave-Server.git
```

2. Change to the project directory:
```sh
cd LightWave-Server
```

3. Install the package with its dependencies:
```sh
pip install -e .
```

Or install from requirements.txt:
```sh
pip install -r requirements.txt
```

### 🎮 Running the Server

There are several ways to run the server:

1. Using the CLI command (if installed with pip):
```sh
lightwave
```

2. Running the module directly:
```sh
python -m lightwave
```

3. Using the main.py entry point with Uvicorn:
```sh
uvicorn main:app --host 0.0.0.0 --port 8080
```

### 🌈 Using Effects

Once the server is running, you can control the LEDs via the API:

1. List available effects:
```sh
curl http://localhost:8080/api/effects
```

2. Get info about a specific effect:
```sh
curl http://localhost:8080/api/effects/RainbowEffect
```

3. Start an effect with custom parameters:
```sh
curl -X POST -H "Content-Type: application/json" -d '{"name": "RainbowEffect", "parameters": {"speed": 1.0, "width": 2.0}}' http://localhost:8080/api/effects/start
```

4. Set a solid color:
```sh
curl -X POST -H "Content-Type: application/json" -d '{"color": "#ff0000"}' http://localhost:8080/api/leds/color
```

5. Change brightness:
```sh
curl -X POST -H "Content-Type: application/json" -d '{"brightness": 0.8}' http://localhost:8080/api/leds/brightness
```

### 🔧 Configuration

LightWave-Server can be configured using environment variables:

| Variable                    | Description                | Default Value |
|-----------------------------|----------------------------|--------------|
| `LIGHTWAVE_HOST`            | Server host                | 0.0.0.0      |
| `LIGHTWAVE_PORT`            | Server port                | 8080         |
| `LIGHTWAVE_DEBUG`           | Debug mode                 | false        |
| `LIGHTWAVE_LOG_LEVEL`       | Log level                  | INFO         |
| `LIGHTWAVE_CORS_ORIGINS`    | CORS origins (comma-separated) | *        |
| `LIGHTWAVE_LED_COUNT`       | Number of LEDs             | 300          |
| `LIGHTWAVE_LED_PIN`         | GPIO pin for LEDs          | D18          |
| `LIGHTWAVE_LED_MODE`        | LED mode (real or mock)    | real         |
| `LIGHTWAVE_LED_BRIGHTNESS`  | Default brightness         | 0.5          |
| `LIGHTWAVE_EFFECT_DEFAULT_FPS` | Default effect FPS      | 30           |

---

## 🧩 API Endpoints

The API provides the following endpoints:

**Effects Endpoints:**
- `GET /api/effects` - Get list of available effects
- `GET /api/effects/{name}` - Get detailed information about an effect
- `GET /api/effects/status` - Get status of the currently running effect
- `POST /api/effects/start` - Start an effect
- `POST /api/effects/stop` - Stop the currently running effect

**LED Control Endpoints:**
- `POST /api/leds/color` - Set the color of all LEDs
- `POST /api/leds/brightness` - Set the brightness of all LEDs
- `POST /api/leds/clear` - Turn off all LEDs

For detailed documentation, visit the OpenAPI docs at `/docs` when the server is running.

---

## ✨ Creating Custom Effects

Creating a custom effect is easy. Just create a new Python file in the `lightwave/effects` directory:

```python
from lightwave.effects.base import Effect, ParameterSpec, ParameterType
from lightwave.utils import get_logger, ColorValue

logger = get_logger(__name__)

class MyCustomEffect(Effect):
    """
    My custom effect description.
    
    More detailed description here.
    """
    
    # Define parameters with metadata
    parameters = [
        ParameterSpec(
            name="speed",
            type=ParameterType.FLOAT,
            description="Speed of the effect",
            default=1.0,
            min_value=0.1,
            max_value=10.0,
        ),
        ParameterSpec(
            name="color",
            type=ParameterType.COLOR,
            description="Primary color",
            default=(255, 0, 0),  # Red
        ),
    ]
    
    def __init__(self, controller, **kwargs):
        """Initialize the effect."""
        super().__init__(controller, **kwargs)
        
        # Initialize state
        self._step = 0
        
        # Set initial FPS
        self.fps = 30
    
    def render_frame(self) -> None:
        """Render a single frame of the effect."""
        # Get parameters
        speed = self.get_parameter("speed")
        color = self.get_parameter("color")
        
        # Implementation goes here
        # Use self.controller to control the LEDs
        
        # Update the display
        self.controller.show()
```

The effect will be automatically discovered and registered when the server starts.

---

## 🤝 Contributing

Contributions are always welcome! Please follow these steps:
1. Fork the repository
2. Create a new branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run the tests and linters
5. Commit your changes (`git commit -m 'Add new feature'`)
6. Push to the branch (`git push origin feature/my-feature`)
7. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/target111/LightWave-Server/LICENSE) file for details.

---