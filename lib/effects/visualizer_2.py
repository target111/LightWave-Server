from lib.led import EffectBase
import socket
import struct
import math
import random
import colorsys


class MusicVisualizer2(EffectBase):
    """
    Layered music visualizer driven by UDP FFT data.
    Bass pulses ripple outward from the center, mids shift hue, treble
    spawns sparkles, and beat hits trigger flashes and color changes.
    """

    CONFIG_SCHEMA = [
        {
            "name": "port",
            "type": "int",
            "default": 5555,
            "description": "UDP port to listen on",
        },
        {
            "name": "smoothing",
            "type": "float",
            "default": 0.4,
            "description": "Temporal smoothing",
        },
        {
            "name": "sensitivity",
            "type": "float",
            "default": 2.5,
            "description": "Overall gain multiplier",
        },
        {
            "name": "beat_threshold",
            "type": "float",
            "default": 1.4,
            "description": "Beat detection threshold",
        },
        {
            "name": "pulse_speed",
            "type": "float",
            "default": 2.0,
            "description": "Speed of bass ripple pulses",
        },
        {
            "name": "sparkle_decay",
            "type": "float",
            "default": 0.88,
            "description": "Treble sparkle fade speed",
        },
        {
            "name": "flash_decay",
            "type": "float",
            "default": 0.4,
            "description": "Beat flash fade speed (0.0=1 frame, 0.9=slow fade)",
        },
        # --- Brightness & Size Tweaks ---
        # Dropped intensity/width back down because pulses now continuously overlap again, creating natural brightness!
        {
            "name": "pulse_intensity",
            "type": "float",
            "default": 1.5,
            "description": "Base multiplier for pulse brightness",
        },
        {
            "name": "beat_multiplier",
            "type": "float",
            "default": 1.5,
            "description": "Extra brightness multiplier for beat hits",
        },
        {
            "name": "pulse_width",
            "type": "float",
            "default": 3.0,
            "description": "Starting width of bass pulses",
        },
        {
            "name": "ambient_brightness",
            "type": "float",
            "default": 0.05,
            "description": "Minimum brightness of the background wave",
        },
    ]

    def __init__(self, led, **kwargs):
        super().__init__(led, **kwargs)

        self.port = int(self.config.get("port", 5555))
        self.smoothing = float(self.config.get("smoothing", 0.4))
        self.sensitivity = float(self.config.get("sensitivity", 2.5))
        self.beat_threshold = float(self.config.get("beat_threshold", 1.4))
        self.pulse_speed = float(self.config.get("pulse_speed", 2.0))
        self.sparkle_decay = float(self.config.get("sparkle_decay", 0.88))
        self.flash_decay = float(self.config.get("flash_decay", 0.4))

        self.pulse_intensity = float(self.config.get("pulse_intensity", 1.5))
        self.beat_multiplier = float(self.config.get("beat_multiplier", 1.5))
        self.pulse_width = float(self.config.get("pulse_width", 3.0))
        self.ambient_brightness = float(self.config.get("ambient_brightness", 0.05))

        n = self.led.count

        # -- frequency band state --
        self._bins: list[float] = []
        self.bass = 0.0
        self.mids = 0.0
        self.treble = 0.0
        self.energy = 0.0

        # -- beat detection --
        self.energy_history: list[float] = [0.0] * 30
        self.energy_idx = 0
        self.beat_cooldown = 0

        # -- hue state --
        self.base_hue = 0.0
        self.beat_hue_offset = 0.0

        # -- visual layers state --
        self.pulses: list[list[float]] = []
        self.sparkle_buffer = [0.0] * n
        self.sparkle_hues = [0.0] * n
        self.flash_level = 0.0
        self.wave_t = 0.0

        # -- per-pixel output buffer --
        self.pixel_r = [0.0] * n
        self.pixel_g = [0.0] * n
        self.pixel_b = [0.0] * n

        # -- UDP socket --
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("0.0.0.0", self.port))
        self._sock.setblocking(False)

    # -- UDP -----------------------------------------------------------------

    def _drain_udp(self) -> list[float] | None:
        latest_data = None
        while True:
            try:
                data, _ = self._sock.recvfrom(4096)
                latest_data = data
            except BlockingIOError:
                break

        if latest_data:
            num_floats = len(latest_data) // 4
            if num_floats > 0:
                return list(
                    struct.unpack(f"<{num_floats}f", latest_data[: num_floats * 4])
                )
        return None

    def _update_bins(self, raw: list[float]):
        if len(self._bins) != len(raw):
            self._bins = [0.0] * len(raw)

        a = self.smoothing
        for i in range(len(raw)):
            v = max(0.0, min(1.0, raw[i])) * self.sensitivity
            self._bins[i] = a * self._bins[i] + (1.0 - a) * v

    def _extract_bands(self):
        n = len(self._bins)
        if n == 0:
            self.bass = self.mids = self.treble = self.energy = 0.0
            return

        bass_end = max(1, n // 4)
        mid_end = max(bass_end + 1, int(n * 0.65))

        self.bass = max(self._bins[:bass_end])
        self.mids = max(self._bins[bass_end:mid_end])
        self.treble = max(self._bins[mid_end:])
        self.energy = sum(self._bins) / n

    def _detect_beat(self) -> bool:
        avg = sum(self.energy_history) / len(self.energy_history)
        self.energy_history[self.energy_idx] = self.energy
        self.energy_idx = (self.energy_idx + 1) % len(self.energy_history)

        if self.beat_cooldown > 0:
            self.beat_cooldown -= 1
            return False

        if avg > 0.01 and self.energy > avg * self.beat_threshold:
            self.beat_cooldown = 6
            return True
        return False

    # -- layers --------------------------------------------------------------

    def _update_hue(self, beat: bool):
        self.base_hue = (self.base_hue + self.mids * 0.003) % 1.0

        if beat:
            self.beat_hue_offset = random.uniform(0.15, 0.45)
        else:
            self.beat_hue_offset *= 0.92

    def _spawn_pulses(self, beat: bool):
        # Cooldown removed! Continuous spawning restores the smooth center core.
        if self.bass > 0.15:
            # We cap at 2.0 so that overlapping doesn't instantly blow out to white
            intensity = min(self.bass * self.pulse_intensity, 2.0)

            if beat:
                intensity *= self.beat_multiplier

            hue = (self.base_hue + self.beat_hue_offset) % 1.0
            self.pulses.append([0.0, intensity, hue])

    def _update_pulses(self):
        n = self.led.count
        center = n / 2.0
        alive = []

        for pos, intensity, hue in self.pulses:
            pos += self.pulse_speed
            intensity *= 0.96

            if intensity < 0.02 or pos > center + 5:
                continue

            width = self.pulse_width + pos * 0.15
            r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 1.0)

            for offset in [-1, 1]:
                pixel_center = center + offset * pos
                lo = max(0, int(pixel_center - width))
                hi = min(n - 1, int(pixel_center + width))

                for j in range(lo, hi + 1):
                    dist = abs(j - pixel_center)
                    falloff = max(0.0, 1.0 - dist / width)
                    strength = intensity * falloff
                    self.pixel_r[j] += r * strength
                    self.pixel_g[j] += g * strength
                    self.pixel_b[j] += b * strength

            alive.append([pos, intensity, hue])

        self.pulses = alive

    def _update_sparkles(self):
        n = self.led.count
        decay = self.sparkle_decay

        for i in range(n):
            self.sparkle_buffer[i] *= decay

        num_new = int(self.treble * 12)
        for _ in range(num_new):
            idx = random.randint(0, n - 1)
            self.sparkle_buffer[idx] = min(1.0, self.treble * 1.5)
            self.sparkle_hues[idx] = (
                self.base_hue + self.beat_hue_offset + random.uniform(-0.1, 0.1)
            ) % 1.0

        for i in range(n):
            if self.sparkle_buffer[i] > 0.05:
                r, g, b = colorsys.hsv_to_rgb(self.sparkle_hues[i], 0.3, 1.0)
                v = self.sparkle_buffer[i]
                self.pixel_r[i] += r * v
                self.pixel_g[i] += g * v
                self.pixel_b[i] += b * v

    def _background_wave(self):
        n = self.led.count
        self.wave_t += 0.02 + self.energy * 0.1

        hue = (self.base_hue + self.beat_hue_offset) % 1.0
        base_brightness = self.ambient_brightness + self.energy * 0.10

        for i in range(n):
            frac = i / max(n - 1, 1)
            wave = (math.sin(frac * 6.0 + self.wave_t) + 1.0) * 0.5
            v = base_brightness * (0.3 + 0.7 * wave)
            pixel_hue = (hue + frac * 0.3) % 1.0
            r, g, b = colorsys.hsv_to_rgb(pixel_hue, 0.7, v)

            self.pixel_r[i] += r
            self.pixel_g[i] += g
            self.pixel_b[i] += b

    def _flash(self, beat: bool):
        if beat:
            self.flash_level = 0.6

        self.flash_level *= self.flash_decay

        if self.flash_level > 0.01:
            n = self.led.count
            for i in range(n):
                self.pixel_r[i] += self.flash_level
                self.pixel_g[i] += self.flash_level
                self.pixel_b[i] += self.flash_level

    # -- main loop -----------------------------------------------------------

    def tick(self):
        raw = self._drain_udp()
        if raw is not None:
            self._update_bins(raw)
        self._extract_bands()

        beat = self._detect_beat()
        self._update_hue(beat)

        n = self.led.count

        # Clear buffers rapidly
        self.pixel_r = [0.0] * n
        self.pixel_g = [0.0] * n
        self.pixel_b = [0.0] * n

        # Apply layers (Additive Blending)
        self._background_wave()
        self._spawn_pulses(beat)
        self._update_pulses()
        self._update_sparkles()
        self._flash(beat)

        # Output to LEDs with clamp
        for i in range(n):
            r = max(0, min(255, int(self.pixel_r[i] * 255)))
            g = max(0, min(255, int(self.pixel_g[i] * 255)))
            b = max(0, min(255, int(self.pixel_b[i] * 255)))
            self.led.set_pixel(i, (r, g, b))

    # -- cleanup -------------------------------------------------------------

    def stop(self):
        super().stop()
        try:
            self._sock.close()
        except OSError:
            pass
