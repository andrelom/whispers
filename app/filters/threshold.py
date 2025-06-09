import numpy as np


class ThresholdPeakDetector:
    def __init__(self, offset_db=10.0, min_distance_hz=5000):
        self.offset_db = offset_db
        self.min_distance_hz = min_distance_hz

    def detect_peaks(self, freqs: np.ndarray, spectrum_db: np.ndarray) -> list[dict]:
        threshold = np.median(spectrum_db) + self.offset_db
        peaks = []
        last_freq = None
        for i in range(1, len(spectrum_db) - 1):
            if (
                spectrum_db[i] > threshold
                and spectrum_db[i] > spectrum_db[i - 1]
                and spectrum_db[i] > spectrum_db[i + 1]
            ):
                freq = freqs[i]
                power = spectrum_db[i]
                if last_freq is None or abs(freq - last_freq) >= self.min_distance_hz:
                    peaks.append({"frequency": freq, "power_db": power})
                    last_freq = freq
        return peaks
