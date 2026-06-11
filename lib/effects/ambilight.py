import math
import random
import socket
import struct

from lib.effects.base import EffectBase, fade_factor

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
            "description": "Temporal smoothing (0.0 = instant, 0.99 = molasses)",
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

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)

        n = self.led.count

        # -- box state (populated on first UDP packet) --
        self.box_colors: list[Rgb] = []
        self.prev_box_colors: list[Rgb] = []

        # -- drift state --
        self.drift_t = 0.0

        # -- sparkle state --
        self.sparkle_buffer = [0.0] * n
        self.scene_activity = 0.0  # 0.0 = calm, 1.0 = very active

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("0.0.0.0", self.port))
        self._sock.setblocking(False)

    def _drain_udp(self) -> list[float] | None:
        """Read all pending packets, keep only the latest."""
        latest = None
        while True:
            try:
                data, _ = self._sock.recvfrom(4096)
                latest = data
            except BlockingIOError:
                break

        if latest:
            num_floats = len(latest) // 4
            if num_floats >= 3 and num_floats % 3 == 0:
                return list(struct.unpack(f"<{num_floats}f", latest[: num_floats * 4]))
        return None

    @staticmethod
    def _parse_boxes(raw: list[float]) -> list[Rgb]:
        """Convert flat float list into (R, G, B) tuples, clamped 0-1."""
        return [
            (
                max(0.0, min(1.0, raw[i])),
                max(0.0, min(1.0, raw[i + 1])),
                max(0.0, min(1.0, raw[i + 2])),
            )
            for i in range(0, len(raw), 3)
        ]

    def _smooth_boxes(self, new_boxes: list[Rgb]):
        """Exponential moving average on box colors for smooth transitions."""
        # Handle box count changes (e.g. capture app reconfigured)
        if len(new_boxes) != len(self.box_colors):
            self.box_colors = list(new_boxes)
            self.prev_box_colors = list(new_boxes)
            return

        self.prev_box_colors = list(self.box_colors)
        a = self.smoothing
        self.box_colors = [
            (
                a * old[0] + (1.0 - a) * new[0],
                a * old[1] + (1.0 - a) * new[1],
                a * old[2] + (1.0 - a) * new[2],
            )
            for old, new in zip(self.box_colors, new_boxes)
        ]

    def _update_scene_activity(self, frames: float):
        """Track how much the colors change between frames (0=calm, 1=active)."""
        if not self.box_colors:
            self.scene_activity *= self._ACTIVITY_IDLE_DECAY**frames
            return

        total_delta = sum(
            abs(c[0] - p[0]) + abs(c[1] - p[1]) + abs(c[2] - p[2])
            for c, p in zip(self.box_colors, self.prev_box_colors)
        )
        activity = min(
            1.0, total_delta / len(self.box_colors) * self._ACTIVITY_GAIN
        )

        smooth = self._ACTIVITY_SMOOTH**frames
        self.scene_activity = (
            smooth * self.scene_activity + (1.0 - smooth) * activity
        )

    @staticmethod
    def _cosine_interp(a: float, b: float, t: float) -> float:
        """Cosine interpolation — smoother than linear at the edges."""
        ft = (1.0 - math.cos(t * math.pi)) * 0.5
        return a * (1.0 - ft) + b * ft

    def _sample_color(self, pos: float) -> Rgb:
        """
        Sample interpolated color at a fractional position (0.0 to 1.0) along
        the box array. Box centers are evenly spaced; colors blend smoothly
        between neighbors using cosine interpolation.
        """
        num_boxes = len(self.box_colors)
        if num_boxes == 0:
            return (0.0, 0.0, 0.0)
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

        return (
            self._cosine_interp(ra, rb, frac),
            self._cosine_interp(ga, gb, frac),
            self._cosine_interp(ba, bb, frac),
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

    def _update_sparkles(self, dt: float):
        decay = fade_factor(dt, self.sparkle_fade)
        for i in range(self.led.count):
            self.sparkle_buffer[i] *= decay

        # Blend the spawn rate between constant and scene-reactive
        reactive = 1.0 + self.scene_activity * self._ACTIVITY_SPARKLE_BOOST
        rate = self.sparkle_rate * (
            1.0 - self.sparkle_scene_reactive
            + self.sparkle_scene_reactive * reactive
        )

        spawn_chance = rate * dt
        for i in range(self.led.count):
            if random.random() < spawn_chance:
                self.sparkle_buffer[i] = min(1.0, self.sparkle_intensity)

    def tick(self, dt: float):
        n = self.led.count
        frames = dt * self.TARGET_FPS

        raw = self._drain_udp()
        if raw is not None:
            new_boxes = self._parse_boxes(raw)
            if new_boxes:
                self._smooth_boxes(new_boxes)

        self._update_scene_activity(frames)

        self.drift_t += self.drift_speed * dt

        sparkle = self.sparkle_intensity > 0
        if sparkle:
            self._update_sparkles(dt)

        buffer = []
        for i in range(n):
            # Base position along the strip (0.0 to 1.0)
            base_pos = i / max(n - 1, 1)

            # Sine-wave drift shifts the sampling point back and forth;
            # clamp so we don't sample outside the color field
            drift_offset = (
                math.sin(
                    self.drift_t * 2.0 * math.pi
                    + base_pos * self._DRIFT_SPATIAL_PHASE
                )
                * self.drift_amount
            )
            shifted_pos = base_pos + drift_offset / max(n - 1, 1)
            shifted_pos = max(0.0, min(1.0, shifted_pos))

            r, g, b = self._sample_color(shifted_pos)
            r, g, b = self._boost_saturation(r, g, b)

            # Additive sparkle overlay blends toward white
            if sparkle and self.sparkle_buffer[i] > self._SPARKLE_VISIBLE:
                spark = self.sparkle_buffer[i]
                r += spark * (1.0 - r)
                g += spark * (1.0 - g)
                b += spark * (1.0 - b)

            buffer.append(
                (
                    max(0, min(255, int(r * self.brightness * 255))),
                    max(0, min(255, int(g * self.brightness * 255))),
                    max(0, min(255, int(b * self.brightness * 255))),
                )
            )

        self.led.set_pixels(buffer)

    def teardown(self):
        try:
            self._sock.close()
        except OSError:
            pass
