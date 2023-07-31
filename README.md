<div align="center">
<h1 align="center">
<img src="https://raw.githubusercontent.com/PKief/vscode-material-icon-theme/ec559a9f6bfd399b82bb44393651661b08aaf7ba/icons/folder-markdown-open.svg" width="100" />
<br>LightWave-Server
</h1>
<h3>◦ LightWave: An HTTP API server for controlling ws281x lights. </h3>

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
- [⚙️ Features](#%EF%B8%8F-features)
- [📂 Project Structure](#-project-structure)
- [🧩 Modules](#-modules)
- [🚀 Getting Started](#-getting-started)
- [🗺 Roadmap](#-roadmap)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

---


## 📍 Overview

The LightWave-Server project is a Python-based server for controlling ws281x LED lights. It provides functionalities for managing presets, setting colors and brightness, and controlling the LED state. The project offers a powerful plugin system that provides total control for creating and managing different effects on LED strips, allowing users to easily create dynamic and visually appealing lighting setups.

---

## ⚙️ Features

| Feature                | Description                                                                                                                                                                                                                |
|------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **⚙️ Architecture**     | The codebase follows a modular design, with separate files for different functionalities such as server control, LED management, and effects. It implements the FastAPI framework to create a RESTful API for controlling the LEDs.                                  |
| **📖 Documentation**    | TBD                                                                                                                                                                                                                              |
| **🔗 Dependencies**     | The core dependencies for the system are the `FastAPI` library for creating the RESTful API and the `adafruit-circuitpython-neopixel` library for controlling the Raspberry Pi GPIO pins. These dependencies are essential for the system to interact with the LED lights and expose the functionality through the API. |
| **🧩 Modularity**       | The codebase demonstrates a decent level of modularity, organizing different functionalities into separate files. This allows components to be developed and maintained independently, making it easier to extend or modify specific parts of the system.                                |
| **✔️ Testing**          | The code lacks explicit tests. The creation of unit tests to verify the behavior and correctness of individual functionalities, as well as integration tests to ensure the system works as a whole, could enhance stability and maintainability.                                          |
| **⚡️ Performance**      | Since the codebase is designed for controlling LED lights, the impact on hardware resources such as CPU and memory should be minimal.                                           |
| **🔐 Security**         | No access control has been implemented for the API server at the moment.          |                                                         |
| **🔌 Integrations**     | A user TUI client is being developed.                 |

---


## 📂 Project Structure




---

## 🧩 Modules

<details closed><summary>Root</summary>

| File                                                                           | Summary                                                                                                                                                                                                                                                                                |
| ---                                                                            | ---                                                                                                                                                                                                                                                                                    |
| [main.py](https://github.com/target111/LightWave-Server.git/blob/main/main.py) | The code snippet imports necessary modules and creates an object of a custom server class (LightWave), with a LED object and an effect registry object passed as arguments. This enables control of LEDs connected to a specific PIN, applying different effects through the registry. |

</details>

<details closed><summary>Lib</summary>

| File                                                                                   | Summary                                                                                                                                                                                                                                                                                                                                                                    |
| ---                                                                                    | ---                                                                                                                                                                                                                                                                                                                                                                        |
| [server.py](https://github.com/target111/LightWave-Server.git/blob/main/lib/server.py) | This code defines a FastAPI application for controlling LED lights. It provides functionalities for managing presets, setting colors and brightness, and controlling the LED state.                                                                                                                                                                                        |
| [led.py](https://github.com/target111/LightWave-Server.git/blob/main/lib/led.py)       | The provided code snippet includes classes and functions for creating and managing LED effects. It consists of an abstract base class for effects, an effect registry, an LED class for controlling the LEDs, and a mock LED class for testing. The code allows for registering and retrieving effects, setting LED colors and brightness, and shows results in real-time. |
| [config.py](https://github.com/target111/LightWave-Server.git/blob/main/lib/config.py) | The code snippet defines the number of LEDs connected to the board and sets the pin used for controlling them.                                                                                                                                                                                                                                                             |

</details>

<details closed><summary>Effects</summary>

| File                                                                                             | Summary                                                                                                                                                                                                                                                                                                                                             |
| ---                                                                                              | ---                                                                                                                                                                                                                                                                                                                                                 |
| [rainbow.py](https://github.com/target111/LightWave-Server.git/blob/main/lib/effects/rainbow.py) | The provided code snippet defines a RainbowCycle class that represents a rainbow effect on an LED strip. It does this by iterating over each pixel on the strip and calculating the RGB values based on the current position in a color wheel. The colors are then set on the pixels and displayed. The effect continues until the code is stopped. |

</details>

---

## 🚀 Getting Started

### ✔️ Prerequisites

Before you begin, ensure that you have the following prerequisites installed:
> - `ℹ️ fastapo[all]`
> - `ℹ️ adafruit-circuitpython-neopixel`

### 📦 Installation

1. Clone the LightWave-Server repository:
```sh
git clone https://github.com/target111/LightWave-Server.git
```

2. Change to the project directory:
```sh
cd LightWave-Server
```

3. Install the dependencies:
```sh
pip install -r requirements.txt
```

### 🎮 Using LightWave-Server

```sh
uvicorn main:app --host 0.0.0.0 --port 8080
```
---


## 🗺 Roadmap

> - [ ] `ℹ️  Task 1: Make sure that an error returns a consistent json response`
> - [ ] `ℹ️  Task 2: Add more effects`
> - [ ] `ℹ️  Task 3: Provide better documentation`


---

## 🤝 Contributing

Contributions are always welcome! Please follow these steps:
1. Fork the project repository. This creates a copy of the project on your account that you can modify without affecting the original project.
2. Clone the forked repository to your local machine using a Git client like Git or GitHub Desktop.
3. Create a new branch with a descriptive name (e.g., `new-feature-branch` or `bugfix-issue-123`).
```sh
git checkout -b new-feature-branch
```
4. Make changes to the project's codebase.
5. Commit your changes to your local branch with a clear commit message that explains the changes you've made.
```sh
git commit -m 'Implemented new feature.'
```
6. Push your changes to your forked repository on GitHub using the following command
```sh
git push origin new-feature-branch
```
7. Create a new pull request to the original project repository. In the pull request, describe the changes you've made and why they're necessary.

---

## 📄 License

This project is licensed under the `ℹ️  MIT` License. See the [LICENSE](https://github.com/target111/LightWave-Server/LICENSE) file for additional info.

---
