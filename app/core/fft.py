import numpy as np

from app.filters.threshold import ThresholdPeakDetector


class FFTProcessor:
    """
    FFTProcessor handles spectral analysis on IQ data using the Fast Fourier Transform (FFT).

    It computes the power spectrum in dB, detects peaks using a configurable threshold detector,
    and estimates the frequency, power, and bandwidth of each detected signal.

    Attributes:
        sample_rate (float): Sample rate of the IQ input stream in Hz.
        detector (ThresholdPeakDetector): Peak detection strategy (configurable).
    """

    def __init__(self, sample_rate: float, threshold_db=10.0, min_distance_hz=5000):
        """
        Initialize the FFT processor.

        Args:
            sample_rate (float): Sample rate of the incoming IQ data (Hz).
            threshold_db (float): Threshold (in dB) above noise floor for detecting peaks.
            min_distance_hz (int): Minimum spacing (Hz) between adjacent detected peaks.
        """
        self.sample_rate = sample_rate
        self.detector = ThresholdPeakDetector(
            offset_db=threshold_db,
            min_distance_hz=min_distance_hz
        )

    def compute_fft_db(self, iq_block: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Compute FFT of the IQ block and convert to decibel (dB) scale.

        Applies a Hann window to reduce spectral leakage.

        Args:
            iq_block (np.ndarray): Input complex64 IQ samples.

        Returns:
            tuple:
                - freqs (np.ndarray): Frequency bins in Hz (centered around 0).
                - spectrum_db (np.ndarray): Power spectrum in dB.
        """
        n = len(iq_block)

        # Apply Hann window to reduce leakage.
        window = np.hanning(n)
        iq_windowed = iq_block * window

        # Compute FFT and shift zero frequency to center.
        fft = np.fft.fftshift(np.fft.fft(iq_windowed))

        # Convert to dB scale.
        magnitude = np.abs(fft)
        spectrum_db = 20 * np.log10(magnitude + 1e-10)  # Small epsilon to avoid log(0).

        # Generate corresponding frequency bins.
        freqs = np.fft.fftshift(np.fft.fftfreq(n, d=1 / self.sample_rate))

        return freqs, spectrum_db

    def extract_peak_regions(self, iq_block: np.ndarray) -> list[dict]:
        """
        Analyze an IQ block to detect frequency regions with significant energy (peaks).

        Args:
            iq_block (np.ndarray): Complex IQ samples.

        Returns:
            list[dict]: Each dictionary includes:
                - "frequency" (float): Center frequency of the peak (Hz).
                - "power_db" (float): Power level at the peak (dB).
                - "index" (int): Index in the FFT array.
                - "bandwidth" (float): Estimated signal width (Hz).
        """
        freqs, spectrum_db = self.compute_fft_db(iq_block)
        peaks = self.detector.detect_peaks(freqs, spectrum_db)

        results = []
        n = len(freqs)
        fft_resolution_hz = self.sample_rate / n  # Hz per FFT bin.

        for peak in peaks:
            freq = peak["frequency"]
            index = np.argmin(np.abs(freqs - freq))  # Closest bin.
            bandwidth = max(self.detector.min_distance_hz, fft_resolution_hz * 10)

            results.append({
                "frequency": freq,
                "power_db": peak["power_db"],
                "index": index,
                "bandwidth": bandwidth,
            })

        return results
