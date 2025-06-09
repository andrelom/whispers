import numpy as np

from app.filters.threshold import ThresholdPeakDetector

class FFTProcessor:
    def __init__(self, sample_rate: float, threshold_db=10.0, min_distance_hz=5000):
        self.sample_rate = sample_rate
        self.detector = ThresholdPeakDetector(offset_db=threshold_db, min_distance_hz=min_distance_hz)

    def compute_fft_db(self, iq_block: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        n = len(iq_block)
        window = np.hanning(n)
        iq_windowed = iq_block * window
        fft = np.fft.fftshift(np.fft.fft(iq_windowed))
        magnitude = np.abs(fft)
        spectrum_db = 20 * np.log10(magnitude + 1e-10)
        freqs = np.fft.fftshift(np.fft.fftfreq(n, d=1 / self.sample_rate))
        return freqs, spectrum_db

    def extract_peak_regions(self, iq_block: np.ndarray) -> list[dict]:
        freqs, spectrum_db = self.compute_fft_db(iq_block)
        peaks = self.detector.detect_peaks(freqs, spectrum_db)
        results = []
        n = len(freqs)
        fft_resolution_hz = self.sample_rate / n
        for peak in peaks:
            freq = peak['frequency']
            index = np.argmin(np.abs(freqs - freq))
            bandwidth = max(self.detector.min_distance_hz, fft_resolution_hz * 10)
            results.append({
                "frequency": freq,
                "power_db": peak['power_db'],
                "index": index,
                "bandwidth": bandwidth,
            })
        return results
