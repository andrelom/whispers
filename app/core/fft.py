import numpy as np

from app.filters.threshold import ThresholdPeakDetector

class FFTProcessor:
    """
    Processes complex IQ samples using FFT to detect and characterize spectral peaks.
    """

    def __init__(self, sample_rate: float, threshold_db=10.0, min_distance_hz=5000):
        """
        Initializes the FFT processor and peak detector.

        Args:
            sample_rate (float): Sampling rate of the IQ signal in Hz.
            threshold_db (float): dB threshold above the noise floor for peak detection.
            min_distance_hz (int): Minimum frequency spacing between detected peaks.
        """
        self.sample_rate = sample_rate
        self.detector = ThresholdPeakDetector(
            offset_db=threshold_db,
            min_distance_hz=min_distance_hz
        )

    def compute_fft_db(self, iq_block: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Computes the FFT and returns frequency bins and power spectrum in dB.

        Args:
            iq_block (np.ndarray): Complex input samples.

        Returns:
            tuple: (frequency bins in Hz, power spectrum in dB)
        """
        n = len(iq_block)

        # Apply Hann window to reduce spectral leakage.
        window = np.hanning(n)
        iq_windowed = iq_block * window

        # Compute FFT and shift zero-frequency component to center.
        fft = np.fft.fftshift(np.fft.fft(iq_windowed))

        # Convert magnitude to dB scale, adding epsilon to avoid log(0).
        magnitude = np.abs(fft)
        spectrum_db = 20 * np.log10(magnitude + 1e-10)

        # Compute corresponding frequency bins.
        freqs = np.fft.fftshift(np.fft.fftfreq(n, d=1 / self.sample_rate))
        return freqs, spectrum_db

    def extract_peak_regions(self, iq_block: np.ndarray) -> list[dict]:
        """
        Identifies spectral peaks and estimates bandwidth around them.

        Args:
            iq_block (np.ndarray): Complex input samples.

        Returns:
            list[dict]: List of peak information including frequency, power, index, and bandwidth.
        """
        # Compute FFT and power spectrum.
        freqs, spectrum_db = self.compute_fft_db(iq_block)
        n = len(freqs)

        # Calculate frequency resolution (Hz per FFT bin).
        bin_width = abs(freqs[1] - freqs[0])

        # Detect peaks and retrieve their FFT bin indices.
        peaks = self.detector.detect_peaks_with_index(freqs, spectrum_db)

        results = []
        for peak in peaks:
            idx = peak["index"]
            center_freq = freqs[idx]

            # Estimate signal bandwidth around the peak using 3dB drop method.
            bw = self._estimate_3db_bandwidth(
                spectrum_db,
                idx,
                bin_width,
                search_window=int(0.5 * self.detector.min_distance_hz / bin_width)
            )

            results.append({
                "frequency": center_freq,
                "power_db": peak["power_db"],
                "index": idx,
                "bandwidth": bw,
            })

        return results

    def _estimate_3db_bandwidth(
        self,
        spectrum_db: np.ndarray,
        peak_idx: int,
        bin_width: float,
        search_window: int
    ) -> float:
        """
        Estimates the 3dB bandwidth of a signal around a given peak.

        Args:
            spectrum_db (np.ndarray): Power spectrum in dB.
            peak_idx (int): Index of the peak in the spectrum.
            bin_width (float): Frequency width per FFT bin in Hz.
            search_window (int): Max number of bins to search on either side of the peak.

        Returns:
            float: Estimated bandwidth in Hz.
        """
        peak_power = spectrum_db[peak_idx]
        threshold = peak_power - 3  # 3dB down from the peak.
        n = len(spectrum_db)

        # Search left for the -3dB point.
        left = peak_idx
        for i in range(max(0, peak_idx - search_window), peak_idx):
            if spectrum_db[i] < threshold:
                left = i
                break

        # Search right for the -3dB point.
        right = peak_idx
        for i in range(peak_idx + 1, min(n, peak_idx + search_window + 1)):
            if spectrum_db[i] < threshold:
                right = i
                break

        # Convert bin span to Hz.
        return (right - left) * bin_width
