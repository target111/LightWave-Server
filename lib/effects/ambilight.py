import colorsys
import math
import random
from collections.abc import Sequence

from lib.effects.base import EffectBase, fade_factor, to_rgb255
from lib.effects.udp import UdpFloatListener

Rgb = tuple[float, float, float]


class Ambilight(EffectBase):
    """
    Screen-reactive ambilight driven by UDP color data.
    """

    # Receives averaged RGB boxes via UDP, interpolates them smoothly
    # across the strip, and adds optional color drift and sparkle layers.
    # Send packed little-endian float32 RGB triplets:
    # [R0,G0,B0, R1,G1,B1, ...] (0.0-1.0).

    CONFIG_SCHEMA = [
        {
            "name": "port",
            "type": "int",
            "default": 5556,
            "description": "UDP port to listen on",
        },
        {
            "name": "smoothing",
            "type": "float",
            "default": 0.6,
            "description": (
                "Temporal smoothing (0.0 = instant, 0.99 = molasses)"
            ),
        },
        {
            "name": "drift_amount",
            "type": "float",
            "default": 3.0,
            "description": "Max sine-wave color drift in pixels (0 = disabled)",
        },
        {
            "name": "drift_speed",
            "type": "float",
            "default": 0.3,
            "description": "Drift oscillations per second",
        },
        {
            "name": "sparkle_intensity",
            "type": "float",
            "default": 0.0,
            "description": "Sparkle brightness (0.0 = off, 1.0 = full white)",
        },
        {
            "name": "sparkle_rate",
            "type": "float",
            "default": 0.6,
            "description": "Average sparkles spawned per pixel per second",
        },
        {
            "name": "sparkle_scene_reactive",
            "type": "float",
            "default": 0.5,
            "description": (
                "How much scene activity boosts sparkles "
                "(0.0 = constant, 1.0 = fully reactive)"
            ),
        },
        {
            "name": "sparkle_fade",
            "type": "float",
            "default": 0.4,
            "description": "Seconds for sparkles to fade out",
        },
        {
            "name": "saturation_boost",
            "type": "float",
            "default": 1.2,
            "description": "Multiplier for color saturation (1.0 = unchanged)",
        },
        {
            "name": "brightness",
            "type": "float",
            "default": 1.0,
            "description": "Overall brightness multiplier",
        },
        {
            "name": "silence_timeout",
            "type": "float",
            "default": 2.0,
            "description": (
                "Seconds without UDP data before easing into the rest animation"
            ),
        },
        {
            "name": "rest_brightness",
            "type": "float",
            "default": 0.12,
            "description": "Peak brightness of the idle rest animation",
        },
    ]

    port: int
    smoothing: float
    drift_amount: float
    drift_speed: float
    sparkle_intensity: float
    sparkle_rate: float
    sparkle_scene_reactive: float
    sparkle_fade: float
    saturation_boost: float
    brightness: float
    silence_timeout: float
    rest_brightness: float

    # Scene-activity signal: per-box color delta scaled to a 0-1 range,
    # then smoothed with a per-frame EMA tuned at TARGET_FPS.
    _ACTIVITY_GAIN = 8.0
    _ACTIVITY_SMOOTH = 0.85
    _ACTIVITY_IDLE_DECAY = 0.95
    # Sparkle spawn rate scales up to (1 + boost) during heavy action
    _ACTIVITY_SPARKLE_BOOST = 4.0
    # Radians of drift phase spread across the strip, so pixels don't
    # all shift in lockstep
    _DRIFT_SPATIAL_PHASE = 1.5
    # Sparkles dimmer than this aren't worth blending in
    _SPARKLE_VISIBLE = 0.02
    # Seconds to crossfade between live colors and the rest animation
    _REST_FADE = 1.5
    # Rest animation: two soft waves lapping in opposite directions under
    # a slow breathing envelope, with a barely-moving hue
    _REST_SAT = 0.5
    _REST_BREATH_PERIOD = 7.0  # seconds per breath cycle
    _REST_HUE_DRIFT = 0.01  # hue cycles per second
    _REST_HUE_SPREAD = 0.10  # hue offset across the strip
    _REST_WAVE_A = (3.0, 0.5)  # (spatial frequency, phase per second)
    _REST_WAVE_B = (5.0, -0.33)

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)

        n = self.led.count

        # -- box state (populated on first UDP packet) --
        self.box_colors: list[Rgb] = []

        # -- drift state --
        self.drift_t = 0.0

        # -- sparkle state --
        self.sparkle_buffer = [0.0] * n
        self.scene_activity = 0.0  # 0.0 = calm, 1.0 = very active
        self._raw_activity = 0.0  # per-packet color delta, pre-smoothing

        # -- rest state --
        # Starts fully at rest until the first packet arrives
        self.rest_blend = 1.0  # 0.0 = live colors, 1.0 = rest animation
        self.rest_t = 0.0
        self._silence_elapsed = 0.0

        self._udp = UdpFloatListener(self.port)

    @staticmethod
    def _parse_boxes(raw: Sequence[float]) -> list[Rgb]:
        """Convert flat float list into (R, G, B) tuples, clamped 0-1."""
        return [
            (
                max(0.0, min(1.0, raw[i])),
                max(0.0, min(1.0, raw[i + 1])),
                max(0.0, min(1.0, raw[i + 2])),
            )
            for i in range(0, len(raw) - 2, 3)
        ]

    def _smooth_boxes(self, new_boxes: list[Rgb]) -> float:
        """Exponential moving average on box colors for smooth transitions.
        Returns how far the smoothed colors moved (the raw scene-activity
        signal, 0-1)."""
        # Handle box count changes (e.g. capture app reconfigured)
        if len(new_boxes) != len(self.box_colors):
            self.box_colors = list(new_boxes)
            return 0.0

        a = self.smoothing
        total_delta = 0.0
        smoothed = []
        for old, new in zip(self.box_colors, new_boxes):
            color = (
                a * old[0] + (1.0 - a) * new[0],
                a * old[1] + (1.0 - a) * new[1],
                a * old[2] + (1.0 - a) * new[2],
            )
            total_delta += (
                abs(color[0] - old[0])
                + abs(color[1] - old[1])
                + abs(color[2] - old[2])
            )
            smoothed.append(color)

        self.box_colors = smoothed
        return min(1.0, total_delta / len(new_boxes) * self._ACTIVITY_GAIN)

    def _update_scene_activity(self, frames: float):
        """Track how much the colors change between frames
        (0=calm, 1=active)."""
        if not self.box_colors:
            self.scene_activity *= self._ACTIVITY_IDLE_DECAY**frames
            return

        smooth = self._ACTIVITY_SMOOTH**frames
        self.scene_activity = (
            smooth * self.scene_activity + (1.0 - smooth) * self._raw_activity
        )
        # The raw signal refreshes only when packets arrive; decay it so a
        # stopped sender reads as calm instead of holding its last delta.
        self._raw_activity *= self._ACTIVITY_IDLE_DECAY**frames

    def _sample_color(self, pos: float) -> Rgb:
        """
        Sample interpolated color at a fractional position (0.0 to 1.0) along
        the box array. Box centers are evenly spaced; colors blend smoothly
        between neighbors using cosine interpolation.
        """
        num_boxes = len(self.box_colors)
        if num_boxes == 1:
            return self.box_colors[0]

        # Map position to box-center space. Box centers sit at 0.5/N,
        # 1.5/N, 2.5/N ... so the first and last box colors extend to
        # the strip edges.
        scaled = pos * num_boxes - 0.5
        idx = math.floor(scaled)
        frac = scaled - idx

        idx_a = max(0, min(num_boxes - 1, idx))
        idx_b = max(0, min(num_boxes - 1, idx + 1))

        ra, ga, ba = self.box_colors[idx_a]
        rb, gb, bb = self.box_colors[idx_b]

        # Cosine interpolation — smoother than linear at the edges
        ft = (1.0 - math.cos(frac * math.pi)) * 0.5
        return (
            ra + (rb - ra) * ft,
            ga + (gb - ga) * ft,
            ba + (bb - ba) * ft,
        )

    def _boost_saturation(self, r: float, g: float, b: float) -> Rgb:
        """Boost saturation to make ambilight colors more vivid on LEDs."""
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        s = self.saturation_boost
        return (
            max(0.0, min(1.0, lum + (r - lum) * s)),
            max(0.0, min(1.0, lum + (g - lum) * s)),
            max(0.0, min(1.0, lum + (b - lum) * s)),
        )

    def _update_rest_blend(self, resting: bool, dt: float):
        """Ease the crossfade toward rest (1.0) or live colors (0.0)."""
        step = dt / self._REST_FADE
        if resting:
            self.rest_blend = min(1.0, self.rest_blend + step)
        else:
            self.rest_blend = max(0.0, self.rest_blend - step)

    def _rest_color(self, frac: float) -> Rgb:
        """Idle animation color at a fractional strip position: a dim,
        slowly breathing glow with two waves lapping in opposite
        directions and a near-static hue."""
        breath = 0.7 + 0.3 * math.sin(
            self.rest_t * 2.0 * math.pi / self._REST_BREATH_PERIOD
        )

        fa, sa = self._REST_WAVE_A
        fb, sb = self._REST_WAVE_B
        wave = (
            math.sin(frac * fa + self.rest_t * sa)
            + math.sin(frac * fb + self.rest_t * sb)
        ) * 0.25 + 0.5

        hue = (
            self.rest_t * self._REST_HUE_DRIFT + frac * self._REST_HUE_SPREAD
        ) % 1.0
        v = self.rest_brightness * breath * (0.3 + 0.7 * wave)
        return colorsys.hsv_to_rgb(hue, self._REST_SAT, v)

    def _render_rest(self):
        """Draw a pure rest frame (no live color data blended in)."""
        n = self.led.count
        span = max(n - 1, 1)
        bright = self.brightness
        self.led.set_pixels(
            [
                to_rgb255(r * bright, g * bright, b * bright)
                for r, g, b in (self._rest_color(i / span) for i in range(n))
            ]
        )

    def _update_sparkles(self, dt: float):
        # Scene activity boosts the spawn rate, scaled by how reactive
        # the user wants sparkles to be
        rate = self.sparkle_rate * (
            1.0
            + self.sparkle_scene_reactive
            * self.scene_activity
            * self._ACTIVITY_SPARKLE_BOOST
        )
        spawn_chance = rate * dt
        decay = fade_factor(dt, self.sparkle_fade)
        intensity = min(1.0, self.sparkle_intensity)

        for i in range(self.led.count):
            if random.random() < spawn_chance:
                self.sparkle_buffer[i] = intensity
            else:
                self.sparkle_buffer[i] *= decay

    def tick(self, dt: float):
        raw = self._udp.drain_latest()
        if raw:
            new_boxes = self._parse_boxes(raw)
            if new_boxes:
                self._silence_elapsed = 0.0
                self._raw_activity = self._smooth_boxes(new_boxes)
        else:
            self._silence_elapsed += dt

        self._update_scene_activity(dt * self.TARGET_FPS)
        self.drift_t += self.drift_speed * dt
        self.rest_t += dt

        # The sender stopped (or hasn't started). Without this the strip
        # would freeze on the last received colors; ease into the rest
        # animation instead.
        resting = (
            not self.box_colors or self._silence_elapsed > self.silence_timeout
        )
        self._update_rest_blend(resting, dt)

        if self.rest_blend >= 1.0 or not self.box_colors:
            # Stale sparkles shouldn't pop back in when the stream resumes
            if any(self.sparkle_buffer):
                self.sparkle_buffer = [0.0] * self.led.count
            self._render_rest()
            return

        sparkle = self.sparkle_intensity > 0
        if sparkle:
            self._update_sparkles(dt)

        n = self.led.count
        span = max(n - 1, 1)
        drifting = self.drift_amount > 0
        drift_phase = self.drift_t * 2.0 * math.pi if drifting else 0.0
        bright = self.brightness
        rest = self.rest_blend

        buffer = []
        for i in range(n):
            # Base position along the strip (0.0 to 1.0)
            frac = i / span
            pos = frac

            # Sine-wave drift shifts the sampling point back and forth;
            # clamp so we don't sample outside the color field
            if drifting:
                offset = (
                    math.sin(drift_phase + pos * self._DRIFT_SPATIAL_PHASE)
                    * self.drift_amount
                )
                pos = max(0.0, min(1.0, pos + offset / span))

            r, g, b = self._sample_color(pos)
            r, g, b = self._boost_saturation(r, g, b)

            # Additive sparkle overlay blends toward white
            if sparkle and self.sparkle_buffer[i] > self._SPARKLE_VISIBLE:
                spark = self.sparkle_buffer[i]
                r += spark * (1.0 - r)
                g += spark * (1.0 - g)
                b += spark * (1.0 - b)

            # Crossfade with the rest animation while entering/leaving it
            if rest > 0.0:
                rr, rg, rb = self._rest_color(frac)
                r = r * (1.0 - rest) + rr * rest
                g = g * (1.0 - rest) + rg * rest
                b = b * (1.0 - rest) + rb * rest

            buffer.append(to_rgb255(r * bright, g * bright, b * bright))

        self.led.set_pixels(buffer)

    def teardown(self):
        self._udp.close()
