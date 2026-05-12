import colorsys
import math
import random
import socket
import struct

from lib.effects.base import EffectBase


class MusicVisualizer(EffectBase):
    """
    Layered music visualizer driven by UDP FFT data.
    Bass pulses ripple outward from the center, mids shift hue, treble
    spawns sparkles, and beat hits trigger flashes and color changes.
    Send packed little-endian float32 values (0.0-1.0) over UDP.
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
            "description": "Temporal smoothing (0.0 = raw, 0.99 = molasses)",
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
            "description": "Beat detection threshold (ratio of current to average energy)",
        },
        {
            "name": "pulse_speed",
            "type": "float",
            "default": 2.0,
            "description": "Speed of bass ripple pulses (pixels per frame)",
        },
        {
            "name": "sparkle_decay",
            "type": "float",
            "default": 0.88,
            "description": "How quickly treble sparkles fade (0.0-0.99)",
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

        n = self.led.count

        # -- frequency band state --
        self._bins: list[float] = []
        self.bass = 0.0
        self.mids = 0.0
        self.treble = 0.0
        self.energy = 0.0

        # -- beat detection --
        # Short-term vs long-term energy comparison (like a compressor's
        # sidechain -- when instantaneous energy spikes above the rolling
        # average, that's a beat)
        self.energy_history: list[float] = [0.0] * 30  # ~0.5s at 60fps
        self.energy_idx = 0
        self.beat_cooldown = 0  # Prevent double-triggers

        # -- hue state --
        self.base_hue = 0.0  # Slowly drifts with mids
        self.beat_hue_offset = 0.0  # Jumps on beat, decays back

        # -- ripple pulses (spawned by bass) --
        # Each pulse: [position_from_center, intensity, hue]
        self.pulses: list[list[float]] = []

        # -- sparkle layer (driven by treble) --
        self.sparkle_buffer = [0.0] * n
        self.sparkle_hues = [0.0] * n

        # -- per-pixel output buffer (RGB floats 0-1) --
        self.pixel_r = [0.0] * n
        self.pixel_g = [0.0] * n
        self.pixel_b = [0.0] * n

        # -- background wave phase --
        self.wave_t = 0.0

        # -- UDP socket --
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("0.0.0.0", self.port))
        self._sock.setblocking(False)

    # -- UDP -----------------------------------------------------------------

    def _drain_udp(self) -> list[float] | None:
        latest = None
        while True:
            try:
                data, _ = self._sock.recvfrom(4096)
            except BlockingIOError:
                break
            num_floats = len(data) // 4
            if num_floats > 0:
                latest = list(struct.unpack(f"<{num_floats}f", data[: num_floats * 4]))
        return latest

    def _update_bins(self, raw: list[float]):
        if len(self._bins) != len(raw):
            self._bins = [0.0] * len(raw)
        a = self.smoothing
        for i in range(len(raw)):
            v = max(0.0, min(1.0, raw[i])) * self.sensitivity
            self._bins[i] = a * self._bins[i] + (1.0 - a) * v

    def _extract_bands(self):
        """Split bins into bass / mids / treble (roughly thirds on log scale)."""
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
            self.beat_cooldown = 6  # ~100ms lockout
            return True
        return False

    # -- layers --------------------------------------------------------------

    def _update_hue(self, beat: bool):
        # Mids slowly rotate the base hue
        self.base_hue += self.mids * 0.003
        if self.base_hue >= 1.0:
            self.base_hue -= 1.0

        # Beats cause a big hue jump that decays
        if beat:
            self.beat_hue_offset = random.uniform(0.15, 0.45)
        else:
            self.beat_hue_offset *= 0.92

    def _spawn_pulses(self, beat: bool):
        if self.bass > 0.15:
            intensity = min(self.bass, 1.5)
            if beat:
                intensity *= 1.8
            hue = (self.base_hue + self.beat_hue_offset) % 1.0
            self.pulses.append([0.0, intensity, hue])

    def _update_pulses(self):
        n = self.led.count
        center = n / 2.0
        alive = []

        for pulse in self.pulses:
            pos, intensity, hue = pulse
            pos += self.pulse_speed
            intensity *= 0.96

            if intensity < 0.02 or pos > center + 5:
                continue

            width = 3.0 + pos * 0.15
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
        """Ambient wave so the strip is never dead, even in quiet moments."""
        n = self.led.count
        self.wave_t += 0.02 + self.energy * 0.1

        hue = self.base_hue + self.beat_hue_offset
        base_brightness = 0.03 + self.energy * 0.08

        for i in range(n):
            frac = i / max(n - 1, 1)
            wave = (math.sin(frac * 6.0 + self.wave_t) + 1.0) * 0.5
            v = base_brightness * (0.3 + 0.7 * wave)
            pixel_hue = (hue + frac * 0.3) % 1.0
            r, g, b = colorsys.hsv_to_rgb(pixel_hue, 0.7, v)
            self.pixel_r[i] += r
            self.pixel_g[i] += g
            self.pixel_b[i] += b

    def _flash(self):
        """Beat flash -- brief white bloom across the whole strip."""
        n = self.led.count
        flash_intensity = 0.5
        for i in range(n):
            self.pixel_r[i] += flash_intensity
            self.pixel_g[i] += flash_intensity
            self.pixel_b[i] += flash_intensity

    # -- main loop -----------------------------------------------------------

    def tick(self):
        raw = self._drain_udp()
        if raw is not None:
            self._update_bins(raw)
        self._extract_bands()

        beat = self._detect_beat()
        self._update_hue(beat)

        n = self.led.count

        for i in range(n):
            self.pixel_r[i] = 0.0
            self.pixel_g[i] = 0.0
            self.pixel_b[i] = 0.0

        # Layer 1: ambient background wave
        self._background_wave()

        # Layer 2: bass ripple pulses from center
        self._spawn_pulses(beat)
        self._update_pulses()

        # Layer 3: treble sparkles
        self._update_sparkles()

        # Layer 4: beat flash
        if beat:
            self._flash()

        # Final output
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
