import numpy as np


class ThresholdPeakDetector:
    """
    A simple threshold-based peak detection algorithm for FFT magnitude spectra.

    This detector identifies local peaks that rise above the noise floor by a defined offset
    (in decibels). It's designed to find strong signals in an FFT output, ignoring noise
    and minor fluctuations.

    Attributes:
        offset_db (float): Power threshold above median noise floor for detection.
        min_distance_hz (int): Minimum spacing between detected peaks to avoid duplicates.
    """

    def __init__(self, offset_db=10.0, min_distance_hz=5000):
        """
        Initialize the peak detector.

        Args:
            offset_db (float): Amount (in dB) above the median spectrum level required for a peak.
            min_distance_hz (int): Minimum frequency spacing (in Hz) between adjacent peaks.
        """
        self.offset_db = offset_db
        self.min_distance_hz = min_distance_hz

    def detect_peaks(self, freqs: np.ndarray, spectrum_db: np.ndarray) -> list[dict]:
        """
        Detect significant peaks in the FFT magnitude spectrum.

        A peak is defined as:
        - A local maximum (greater than its neighbors),
        - Above the computed threshold (median + offset),
        - Not too close to another previously detected peak.

        Args:
            freqs (np.ndarray): Array of frequency bins (in Hz), same length as spectrum.
            spectrum_db (np.ndarray): Power spectrum in dB, same length as freqs.

        Returns:
            list[dict]: Each dictionary contains:
                - "frequency": frequency of the peak (Hz)
                - "power_db": power level at the peak (dB)
        """
        # Dynamic threshold based on median + offset.
        threshold = np.median(spectrum_db) + self.offset_db
        peaks = []
        last_freq = None

        for i in range(1, len(spectrum_db) - 1):
            # Check for a local maximum above the threshold.
            if (
                spectrum_db[i] > threshold
                and spectrum_db[i] > spectrum_db[i - 1]
                and spectrum_db[i] > spectrum_db[i + 1]
            ):
                freq = freqs[i]
                power = spectrum_db[i]

                # Skip peaks that are too close to the previous one.
                if last_freq is None or abs(freq - last_freq) >= self.min_distance_hz:
                    peaks.append({"frequency": freq, "power_db": power})
                    last_freq = freq

        return peaks
