from typing import Annotated, List
from fastapi import FastAPI, Body, HTTPException, Path
from pydantic_extra_types.color import Color

class LightWave(FastAPI):
    def __init__(self, led, effect_registry):
        super().__init__()
        self.led = led
        self.effect_registry = effect_registry

        self.running = None

        @self.get("/presets")
        def show_presets():
            """
            Get a list of all available presets

            Returns:
                dict: A json array containing a list of all available presets
            """
            return {
                "presets": [
                    {
                        "name": name,
                        "description": self.effect_registry.get_description(name),
                    }
                    for name in self.effect_registry.get_names()
                ]
            }

        @self.get("/presets/running")
        def get_running_preset():
            """
            Get information about the currently running preset

            Returns:
                dict: A json object containing information about the currently running preset
            """
            if not self.running:
                raise HTTPException(status_code=404, detail="No preset running")

            return {
                "name": self.running.__class__.__name__,
                "description": self.effect_registry.get_description(
                    self.running.__class__.__name__,
                ),
                "start_time": self.running.start_time.isoformat(),
                "duration": (
                    self.running.start_time.now() - self.running.start_time
                ).seconds,
            }

        @self.get("/presets/{preset_name}")
        def get_preset_info(preset_name: Annotated[str, Path(description="Name of the preset to get info about")]):
            """
            Get information about a specific preset

            Args:
                preset_name (str): Name of the preset to get info about

            Returns:
                dict: A json object containing information about the preset
            """
            if not self.effect_registry.is_effect(preset_name):
                raise HTTPException(status_code=404, detail="Preset not found")

            return {
                "description": self.effect_registry.get_description(preset_name),
            }

        @self.post("/presets/start")
        def start_preset(preset_name: Annotated[str, Body(embed=True, description="Name of the preset to start")]):
            """
            Start a preset

            Args:
                preset_name (str): Name of the preset to start

            Returns:
                Null
            """
            if self.running:
                self.running.stop()
                self.running = None

            if not self.effect_registry.is_effect(preset_name):
                raise HTTPException(status_code=404, detail="Preset not found")

            self.running = self.effect_registry.get(preset_name)(self.led)
            self.running.start()

        @self.post("/presets/stop")
        def stop_preset():
            """
            Stop the currently running preset

            Returns:
                Null
            """
            if not self.running:
                raise HTTPException(status_code=404, detail="No preset running")

            self.running.stop()
            self.running = None
            self.led.clear()

        @self.post("/leds/color/set")
        def set_color_rgb(
            color: Annotated[
                Color,
                Body(
                    embed=True,
                    description="A color type which supports many formats like hex, rgb, hsl, hsv, etc.",
                ),
            ]
        ):
            """
            Set the color of the LEDs

            Args:
                color (Color): A color type which supports many formats like hex, rgb, hsl, hsv, etc.

            Returns:
                Null
            """
            if self.running:
                raise HTTPException(status_code=400, detail="Preset already running")

            self.led.set_color(color.as_rgb_tuple())

        @self.post("/leds/color/brightness")
        def set_brightness(
            brightness: Annotated[
                float,
                Body(
                    ...,
                    ge=0.0,
                    le=1.0,
                    embed=True,
                    description="Brightness value in float range 0-100",
                ),
            ]
        ):
            """
            Set the brightness of the LEDs

            Args:
                brightness (float): Brightness value in float range 0.0 - 1.0

            Returns:
                Null
            """
            self.led.set_brightness(brightness)

        @self.post("/leds/color/clear")
        def clear_color():
            """
            Clear the color of the LEDs

            Returns:
                Null
            """
            if self.running:
                raise HTTPException(status_code=400, detail="Preset already running")

            self.led.clear()

        @self.post("/leds/color/red")
        def set_red():
            """
            Set the color of the LEDs to red

            Returns:
                Null
            """
            if self.running:
                raise HTTPException(status_code=400, detail="Preset already running")

            self.led.set_color((255, 0, 0))

        @self.post("/leds/color/green")
        def set_green():
            """
            Set the color of the LEDs to green

            Returns:
                Null
            """
            if self.running:
                raise HTTPException(status_code=400, detail="Preset already running")

            self.led.set_color((0, 255, 0))

        @self.post("/leds/color/blue")
        def set_blue():
            """
            Set the color of the LEDs to blue

            Returns:
                Null
            """
            if self.running:
                raise HTTPException(status_code=400, detail="Preset already running")

            self.led.set_color((0, 0, 255))

        @self.on_event("shutdown")
        def shutdown_event():
            """
            Stop the currently running preset and clear the LEDs on shutdown

            Returns:
                Null
            """
            if self.running:
                self.running.stop()
                self.running = None

            self.led.clear()