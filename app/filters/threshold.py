import numpy as np


class ThresholdPeakDetector:
    """
    A robust threshold-based peak detection algorithm for FFT magnitude spectra.

    Improvements:
    1. Uses noise floor estimation (median) instead of mean for better noise immunity
    2. Includes endpoint handling for local maxima
    3. Implements proper non-maximum suppression for peak spacing
    4. Handles single-point spectra edge cases

    Attributes:
        offset_db (float): Power threshold above median noise floor for detection.
        min_distance_hz (int): Minimum frequency spacing (in Hz) between adjacent peaks.
    """

    def __init__(self, offset_db=10.0, min_distance_hz=5000):
        """
        Initialize the peak detector.

        Args:
            offset_db (float): Threshold above median noise floor (in dB).
            min_distance_hz (int): Minimum spacing between accepted peaks (in Hz).
        """
        self.offset_db = offset_db
        self.min_distance_hz = min_distance_hz

    def detect_peaks(self, freqs: np.ndarray, spectrum_db: np.ndarray) -> list[dict]:
        """
        Detect significant peaks in a dB spectrum.

        Args:
            freqs (np.ndarray): Frequency bin centers in Hz.
            spectrum_db (np.ndarray): Power values in dB.

        Returns:
            list[dict]: List of detected peaks with frequency and power.
        """
        # Delegate to full method but discard index if not needed.
        return [
            {"frequency": p["frequency"], "power_db": p["power_db"]}
            for p in self.detect_peaks_with_index(freqs, spectrum_db)
        ]

    def detect_peaks_with_index(self, freqs: np.ndarray, spectrum_db: np.ndarray) -> list[dict]:
        """
        Detect peaks and return results including their FFT bin index.

        Args:
            freqs (np.ndarray): Frequency bin centers in Hz.
            spectrum_db (np.ndarray): Power values in dB.

        Returns:
            list[dict]: Detected peaks including frequency, power, and FFT index.
        """
        # Handle empty input case.
        if len(spectrum_db) == 0:
            return []

        # Estimate noise floor using robust median.
        noise_floor = np.median(spectrum_db)
        threshold = noise_floor + self.offset_db

        peaks = []
        n = len(spectrum_db)
        candidates = []

        # Identify candidate peaks as local maxima above threshold.
        for i in range(n):
            # Left edge case.
            if i == 0:
                if n > 1 and spectrum_db[i] > threshold and spectrum_db[i] > spectrum_db[i + 1]:
                    candidates.append(i)
                elif n == 1 and spectrum_db[i] > threshold:
                    candidates.append(i)
            # Right edge case.
            elif i == n - 1:
                if spectrum_db[i] > threshold and spectrum_db[i] > spectrum_db[i - 1]:
                    candidates.append(i)
            # Middle points.
            else:
                if (spectrum_db[i] > threshold and
                    spectrum_db[i] > spectrum_db[i - 1] and
                    spectrum_db[i] > spectrum_db[i + 1]):
                    candidates.append(i)

        # Sort by descending power so strongest peaks are prioritized.
        candidates.sort(key=lambda i: spectrum_db[i], reverse=True)
        accepted_freqs = []

        # Apply non-maximum suppression by checking min frequency spacing.
        for i in candidates:
            freq = freqs[i]
            power = spectrum_db[i]

            # Reject if too close to a previously accepted peak.
            too_close = any(
                abs(freq - accepted_freq) < self.min_distance_hz
                for accepted_freq in accepted_freqs
            )

            if not too_close:
                peaks.append({
                    "frequency": freq,
                    "power_db": power,
                    "index": i # Include FFT bin index for later use (e.g., bandwidth estimation).
                })
                accepted_freqs.append(freq)

        # Sort final output by frequency (ascending) for consistency.
        peaks.sort(key=lambda p: p["frequency"])
        return peaks
