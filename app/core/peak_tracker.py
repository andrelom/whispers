import time
from collections import defaultdict


class PeakTracker:
    """
    Tracks the stability of detected spectral peaks over time.

    The idea is to reduce false positives by confirming only those peaks that appear
    consistently over multiple scan cycles. It stores a history of peak detections
    (by rounded frequency) and filters out unstable or transient spikes.

    Attributes:
        min_hits (int): Minimum number of detections required to consider a peak stable.
        window_sec (int): Time window (in seconds) in which those detections must occur.
        history (dict[int, list[float]]): Maps frequency (rounded Hz) to list of detection timestamps.
    """

    def __init__(self, min_hits=3, window_sec=10):
        """
        Initialize the peak tracker.

        Args:
            min_hits (int): How many detections are required to consider a frequency stable.
            window_sec (int): The maximum age (in seconds) of a detection to count toward stability.
        """
        self.min_hits = min_hits
        self.window_sec = window_sec
        self.history = defaultdict(list)

    def update_and_filter(self, detected_peaks: list[dict]) -> list[dict]:
        """
        Update the tracker with the latest detected peaks and return only the stable ones.

        This method:
        - Records the current time for each newly detected frequency.
        - Discards stale detections (older than the time window).
        - Keeps only those frequencies that meet the min_hits requirement.
        - Returns the original peak dicts that correspond to the stable frequencies.

        Args:
            detected_peaks (list[dict]): Each dict should contain a 'frequency' key (Hz).

        Returns:
            list[dict]: List of stable peaks (subset of input).
        """
        now = time.time()
        stable_peaks = []

        # Record current timestamp for each detected peak frequency.
        for peak in detected_peaks:
            freq = round(peak["frequency"])  # Round to eliminate small jitter.
            self.history[freq].append(now)

        # Clean up and check for stability.
        for freq, timestamps in list(self.history.items()):
            # Keep only recent timestamps within the time window.
            self.history[freq] = [t for t in timestamps if now - t <= self.window_sec]

            if not self.history[freq]:
                # Remove frequency entry if no recent detections remain.
                del self.history[freq]
                continue

            if len(self.history[freq]) >= self.min_hits:
                # Confirmed stable peak, return the original peak info.
                for peak in detected_peaks:
                    if round(peak["frequency"]) == freq:
                        stable_peaks.append(peak)
                        break

        return stable_peaks

    def clear(self):
        """
        Reset the detection history, removing all stored peak data.
        """
        self.history.clear()
