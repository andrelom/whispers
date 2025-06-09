import time
from collections import defaultdict


class PeakTracker:
    """
    Tracks the stability of detected spectral peaks over time.

    This class helps reduce false positives by confirming only those frequency peaks
    that appear repeatedly within a rolling time window. Useful in SDR and signal
    detection systems to eliminate transient or spurious peaks.

    Attributes:
        min_hits (int): Minimum number of detections required to consider a frequency stable.
        window_sec (int): Rolling time window (in seconds) to track peak occurrences.
        history (dict[int, list[float]]): Maps rounded frequency (Hz) to list of detection timestamps.
    """

    def __init__(self, min_hits=3, window_sec=10):
        """
        Initialize the PeakTracker with configuration parameters.

        Args:
            min_hits (int): Minimum number of detections within the time window to confirm a stable peak.
            window_sec (int): Duration of the rolling window in seconds.
        """
        self.min_hits = min_hits
        self.window_sec = window_sec
        self.history = defaultdict(list)  # Maps frequency buckets to list of timestamps.

    def update_and_filter(self, detected_peaks: list[dict]) -> list[dict]:
        """
        Update the tracker with newly detected peaks and return those considered stable.

        Args:
            detected_peaks (list[dict]): List of peak dicts, each with at least:
                - 'frequency': float (Hz)
                - 'power_db': float (dB)

        Returns:
            list[dict]: List of stable peak dicts (strongest per frequency bucket).
        """
        now = time.time()
        current_peaks = {}   # Map: freq_bucket -> strongest peak (this scan).
        stable_peaks = []    # Final list of stable peak dicts to return.

        # Step 1: Deduplicate current peaks by frequency bucket.
        for peak in detected_peaks:
            freq_bucket = round(peak["frequency"])  # Round to integer Hz.
            # Keep only the strongest peak per bucket (by power).
            if (freq_bucket not in current_peaks or
                peak["power_db"] > current_peaks[freq_bucket]["power_db"]):
                current_peaks[freq_bucket] = peak

        # Step 2: Update history with current detections.
        for freq_bucket in current_peaks:
            self.history[freq_bucket].append(now)

        # Step 3: Prune old detections and determine stable frequencies.
        stable_freqs = set()
        for freq_bucket, timestamps in list(self.history.items()):
            # Remove timestamps outside the rolling window.
            recent = [t for t in timestamps if now - t <= self.window_sec]

            if not recent:
                # If all timestamps are stale, remove the frequency from history.
                del self.history[freq_bucket]
                continue

            self.history[freq_bucket] = recent  # Update with only recent entries.

            # If enough recent detections, mark frequency as stable.
            if len(recent) >= self.min_hits:
                stable_freqs.add(freq_bucket)

        # Step 4: Collect current peaks that are now considered stable.
        for freq_bucket in stable_freqs:
            if freq_bucket in current_peaks:
                stable_peaks.append(current_peaks[freq_bucket])

        return stable_peaks

    def clear(self):
        """
        Clear all tracked history.

        This is useful when resetting the tracker or changing scanning context (e.g. band switch).
        """
        self.history.clear()
