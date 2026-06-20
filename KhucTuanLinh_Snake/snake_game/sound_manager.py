"""Quản lý âm thanh: tự sinh hiệu ứng âm thanh bằng numpy (nếu có) và phát qua pygame.mixer."""
import pygame

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


class SoundManager:
    SAMPLE_RATE = 44100

    def __init__(self):
        self.enabled = False
        self.muted = False
        self.sounds = {}

        try:
            pygame.mixer.pre_init(self.SAMPLE_RATE, -16, 1, 256)
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=self.SAMPLE_RATE, size=-16, channels=1)
            self.enabled = True
        except pygame.error as e:
            print(f"[SoundManager] mixer unavailable: {e}")
            self.enabled = False
            return

        if not NUMPY_AVAILABLE:
            print("[SoundManager] numpy missing, sounds disabled")
            self.enabled = False
            return

        try:
            self.sounds["eat"] = self._tone_blip(880, 1320, 0.09, square_mix=0.25)
            self.sounds["turn"] = self._tone_blip(300, 340, 0.03, square_mix=0.0, vol=0.18)
            self.sounds["crash"] = self._crash_sound()
            self.sounds["start"] = self._tone_blip(440, 880, 0.18, square_mix=0.15)
        except Exception as e:
            print(f"[SoundManager] generation failed: {e}")
            self.enabled = False

    def _envelope(self, n, attack=0.05, release=0.6):
        env = np.ones(n, dtype=np.float32)
        a = max(1, int(n * attack))
        r = max(1, int(n * release))
        env[:a] = np.linspace(0, 1, a)
        env[-r:] *= np.linspace(1, 0, r)
        return env

    def _to_sound(self, wave):
        wave = np.clip(wave, -1.0, 1.0)
        int_wave = np.ascontiguousarray((wave * 32767).astype(np.int16))
        return pygame.sndarray.make_sound(int_wave)

    def _tone_blip(self, f_start, f_end, duration, square_mix=0.2, vol=0.5):
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n, endpoint=False)
        freq_sweep = np.linspace(f_start, f_end, n)
        phase = 2 * np.pi * np.cumsum(freq_sweep) / self.SAMPLE_RATE
        wave = np.sin(phase) * (1 - square_mix)
        if square_mix > 0:
            wave += square_mix * np.sign(np.sin(phase))
        wave *= self._envelope(n, attack=0.02, release=0.7) * vol
        return self._to_sound(wave.astype(np.float32))

    def _crash_sound(self):
        duration = 0.4
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n, endpoint=False)
        thud = np.sin(2 * np.pi * 75 * t) * np.exp(-t * 7)
        noise = (np.random.rand(n).astype(np.float32) * 2 - 1) * np.exp(-t * 10)
        wave = thud * 0.65 + noise * 0.55
        wave *= self._envelope(n, attack=0.005, release=0.85) * 0.8
        return self._to_sound(wave.astype(np.float32))

    def play(self, name):
        if not self.enabled or self.muted:
            return
        s = self.sounds.get(name)
        if s:
            s.play()

    def toggle_mute(self):
        self.muted = not self.muted
