import colorsys
import math
import random
from collections.abc import Sequence

from lib.effects.anim import Spawner, fade_factor
from lib.effects.base import EffectBase, option
from lib.effects.colors import to_rgb255
from lib.effects.udp import UdpFloatListener


class MusicVisualizer(EffectBase):
    """
    Layered music visualizer driven by UDP FFT data.
    """

    # Bass pulses ripple outward from the center, mids shift hue, treble
    # spawns sparkles, and beat hits trigger flashes and color changes.
    # Send packed little-endian float32 values (0.0-1.0) over UDP.

    port: int = option(5555, "UDP port to listen on", min=0, max=65535)
    smoothing: float = option(
        0.4,
        "Temporal smoothing (0.0 = raw, 0.99 = molasses)",
        min=0.0,
        max=0.99,
    )
    sensitivity: float = option(2.5, "Overall gain multiplier", min=0.0)
    beat_threshold: float = option(
        1.4, "Beat detection threshold (current vs average energy)", min=1.0
    )
    pulse_speed: float = option(
        120.0, "Speed of bass ripple pulses (pixels per second)", min=0.0
    )
    sparkle_fade: float = option(
        0.4, "Seconds for treble sparkles to fade out", min=0.0
    )
    flash_fade: float = option(
        0.05, "Seconds for the beat flash to fade out", min=0.0
    )
    pulse_intensity: float = option(
        1.5, "Base multiplier for pulse brightness", min=0.0
    )
    beat_multiplier: float = option(
        1.5, "Extra brightness multiplier for beat hits", min=0.0
    )
    pulse_width: float = option(
        3.0, "Starting width of bass pulses", min=0.1
    )
    ambient_brightness: float = option(
        0.05, "Minimum brightness of the background wave", min=0.0, max=1.0
    )
    silence_timeout: float = option(
        0.5, "Seconds without UDP data before fading to ambient", min=0.0
    )

    _BEAT_COOLDOWN = 0.1  # seconds of lockout after a beat hit
    _HUE_DRIFT_RATE = 0.18  # hue cycles/second at mids=1.0
    _BEAT_HUE_FADE = 0.6  # seconds for the beat hue offset to fade out
    _PULSE_SPAWN_RATE = 60.0  # pulses spawned/second while bass is hot
    _PULSE_FADE = 1.2  # seconds for a pulse to fade out
    _SPARKLE_SPAWN_RATE = 720.0  # sparkles spawned/second at treble=1.0
    _WAVE_SPEED = 1.2  # background wave phase/second at silence
    _WAVE_ENERGY_BOOST = 6.0  # extra wave phase/second at energy=1.0

    def setup(self):
        n = self.n

        # -- frequency band state --
        self._bins: list[float] = []
        self.bass = 0.0
        self.mids = 0.0
        self.treble = 0.0
        self.energy = 0.0

        # -- beat detection --
        self.energy_history: list[float] = [0.0] * 30
        self.energy_idx = 0
        self.beat_cooldown = 0.0

        # -- hue state --
        self.base_hue = 0.0
        self.beat_hue_offset = 0.0

        # -- visual layers state --
        # Each pulse: [position_from_center, intensity, hue]
        self.pulses: list[list[float]] = []
        self.sparkle_buffer = [0.0] * n
        self.sparkle_hues = [0.0] * n
        self.flash_level = 0.0
        self.wave_t = 0.0

        # -- per-pixel output buffer (RGB floats 0-1) --
        self.pixel_r = [0.0] * n
        self.pixel_g = [0.0] * n
        self.pixel_b = [0.0] * n

        self._silence_elapsed = 0.0
        # Spawners accumulate fractional spawns so slower/faster loops
        # produce the same rate per second.
        self._pulse_spawner = Spawner(self._PULSE_SPAWN_RATE)
        self._sparkle_spawner = Spawner()

        self._udp = UdpFloatListener(self.port)

    def _update_bins(self, raw: Sequence[float]):
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

        # Tiny packets (n < 3) leave the upper band slices empty
        self.bass = max(self._bins[:bass_end])
        self.mids = max(self._bins[bass_end:mid_end], default=0.0)
        self.treble = max(self._bins[mid_end:], default=0.0)
        self.energy = sum(self._bins) / n

    def _detect_beat(self, dt: float) -> bool:
        avg = sum(self.energy_history) / len(self.energy_history)
        self.energy_history[self.energy_idx] = self.energy
        self.energy_idx = (self.energy_idx + 1) % len(self.energy_history)

        if self.beat_cooldown > 0:
            self.beat_cooldown -= dt
            return False

        if avg > 0.01 and self.energy > avg * self.beat_threshold:
            self.beat_cooldown = self._BEAT_COOLDOWN
            return True
        return False

    def _update_hue(self, beat: bool, dt: float):
        self.base_hue = (
            self.base_hue + self.mids * self._HUE_DRIFT_RATE * dt
        ) % 1.0

        if beat:
            self.beat_hue_offset = random.uniform(0.15, 0.45)
        else:
            self.beat_hue_offset *= fade_factor(dt, self._BEAT_HUE_FADE)

    def _spawn_pulses(self, beat: bool, dt: float):
        if self.bass <= 0.15:
            self._pulse_spawner.reset()
            return

        for _ in range(self._pulse_spawner.poll(dt)):
            # Cap so overlapping pulses don't instantly blow out to white
            intensity = min(self.bass * self.pulse_intensity, 2.0)
            if beat:
                intensity *= self.beat_multiplier

            hue = (self.base_hue + self.beat_hue_offset) % 1.0
            self.pulses.append([0.0, intensity, hue])

    def _update_pulses(self, dt: float):
        n = self.n
        center = n / 2.0
        alive = []

        pulse_decay = fade_factor(dt, self._PULSE_FADE)

        for pos, intensity, hue in self.pulses:
            pos += self.pulse_speed * dt
            intensity *= pulse_decay

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

    def _update_sparkles(self, dt: float):
        n = self.n
        decay = fade_factor(dt, self.sparkle_fade)

        for i in range(n):
            self.sparkle_buffer[i] *= decay

        num_new = self._sparkle_spawner.poll(
            dt, rate=self.treble * self._SPARKLE_SPAWN_RATE
        )
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

    def _background_wave(self, dt: float):
        n = self.n
        self.wave_t += (
            self._WAVE_SPEED + self.energy * self._WAVE_ENERGY_BOOST
        ) * dt

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

    def _flash(self, beat: bool, dt: float):
        if beat:
            self.flash_level = 0.6

        self.flash_level *= fade_factor(dt, self.flash_fade)

        if self.flash_level > 0.01:
            for i in range(self.n):
                self.pixel_r[i] += self.flash_level
                self.pixel_g[i] += self.flash_level
                self.pixel_b[i] += self.flash_level

    def tick(self, dt: float):
        raw = self._udp.drain_latest()
        if raw is not None:
            self._silence_elapsed = 0.0
            self._update_bins(raw)
        else:
            self._silence_elapsed += dt
            if self._silence_elapsed > self.silence_timeout and any(
                b > 1e-4 for b in self._bins
            ):
                # The sender stopped (or died mid-stream). Without this the
                # bins freeze at their last values and the effect keeps
                # replaying the final frame; feed silence so it decays back
                # to the ambient wave.
                self._update_bins([0.0] * len(self._bins))
        self._extract_bands()

        beat = self._detect_beat(dt)
        self._update_hue(beat, dt)

        n = self.n

        self.pixel_r = [0.0] * n
        self.pixel_g = [0.0] * n
        self.pixel_b = [0.0] * n

        # Layers blend additively into the pixel buffer
        self._background_wave(dt)
        self._spawn_pulses(beat, dt)
        self._update_pulses(dt)
        self._update_sparkles(dt)
        self._flash(beat, dt)

        self.pixels = [
            to_rgb255(self.pixel_r[i], self.pixel_g[i], self.pixel_b[i])
            for i in range(n)
        ]

    def teardown(self):
        self._udp.close()
