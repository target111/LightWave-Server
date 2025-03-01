"""
Setup script for the LightWave-Server package.
"""

from setuptools import setup, find_packages

setup(
    name="lightwave",
    version="2.0.0",
    description="HTTP API server for controlling ws281x LED lights",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="target111",
    url="https://github.com/target111/LightWave-Server",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.95.0",
        "uvicorn>=0.21.0",
        "adafruit-circuitpython-neopixel>=6.3.7",
        "pydantic>=2.0.0",
        "pydantic-extra-types>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.3.1",
            "black>=23.3.0",
            "ruff>=0.0.261",
            "mypy>=1.2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "lightwave=lightwave.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
)