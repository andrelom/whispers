import time
import numpy as np

from collections import deque


class FrequencyObserver:
    """
    Tracks activity patterns on individual frequencies to distinguish speech-like signals
    (bursty, intermittent) from continuous transmissions (e.g., FM music, digital carriers).

    Features:
    - Tracks active time segments, not individual samples
    - Computes coefficient of variation to assess signal stability
    - Calculates real duty cycle based on time duration
    - Uses deque for memory-efficient segment tracking and automatic pruning
    """

    def __init__(self, window_sec=30, min_activity_sec=0.1, activity_threshold_db=6.0):
        """
        Initialize the observer with configuration parameters.

        Args:
            window_sec (float): Time window for observing signal behavior (in seconds).
            min_activity_sec (float): Minimum duration to consider a segment valid (not used yet).
            activity_threshold_db (float): Offset below mean to define activity (in dB).
        """
        self.window_sec = window_sec
        self.min_activity_sec = min_activity_sec
        self.activity_threshold_db = activity_threshold_db

        # Logs activity as time segments per frequency: {freq_bucket: deque[(start_time, end_time)]}.
        self.activity_log = {}

        # Stores running power stats: {freq_bucket: [sum, sum_sq, count]}.
        self.power_stats = {}

        # Tracks the timestamp of the last power update per frequency.
        self.last_update = {}

    def update(self, freq: float, power: float):
        """
        Feed a new power measurement for a given frequency.

        Args:
            freq (float): Frequency in Hz.
            power (float): Signal strength in dB.
        """
        now = time.time()
        freq_bucket = round(freq)  # Normalize frequency key for binning.

        # Initialize tracking structures if this is the first time we've seen this frequency.
        if freq_bucket not in self.activity_log:
            self.activity_log[freq_bucket] = deque()
            self.power_stats[freq_bucket] = [0.0, 0.0, 0]
            self.last_update[freq_bucket] = now
            return

        # Update power statistics (mean and variance).
        stats = self.power_stats[freq_bucket]
        stats[0] += power               # sum of powers.
        stats[1] += power * power       # sum of squares.
        stats[2] += 1                   # count.

        # Determine dynamic threshold: signal is "active" if above (mean - X dB).
        mean_power = stats[0] / stats[2]
        is_active = power > (mean_power - self.activity_threshold_db)
        last_time = self.last_update[freq_bucket]

        # Extend or start an activity segment based on activity.
        if is_active:
            if self.activity_log[freq_bucket] and now - last_time < 1.0:
                # Extend the last segment.
                start, _ = self.activity_log[freq_bucket].pop()
                self.activity_log[freq_bucket].append((start, now))
            else:
                # Start a new activity segment.
                self.activity_log[freq_bucket].append((now, now))
        else:
            # If inactive and the last update was active, close the segment.
            if self.activity_log[freq_bucket] and self.activity_log[freq_bucket][-1][1] == last_time:
                start, _ = self.activity_log[freq_bucket].pop()
                self.activity_log[freq_bucket].append((start, last_time))

        # Update last timestamp and remove old data.
        self.last_update[freq_bucket] = now
        self._prune_old_entries(freq_bucket, now)

    def _prune_old_entries(self, freq_bucket: int, now: float):
        """
        Remove activity segments and power stats older than the configured time window.

        Args:
            freq_bucket (int): Frequency bucket key.
            now (float): Current timestamp.
        """
        # Remove segments where end time is older than the time window.
        while self.activity_log[freq_bucket]:
            start, end = self.activity_log[freq_bucket][0]
            if now - end > self.window_sec:
                self.activity_log[freq_bucket].popleft()
            else:
                break

        # If no recent activity remains, reset power stats.
        if not self.activity_log[freq_bucket]:
            self.power_stats[freq_bucket] = [0.0, 0.0, 0]

    def is_continuous(self, freq: float, duty_cycle_thresh=0.7, cv_thresh=0.2) -> bool:
        """
        Determine whether a frequency is showing a continuous signal.

        Args:
            freq (float): Frequency to check.
            duty_cycle_thresh (float): Threshold for minimum active duty cycle [0.0-1.0].
            cv_thresh (float): Coefficient of variation threshold (lower means more stable).

        Returns:
            bool: True if signal appears continuous (e.g., FM station).
        """
        freq_bucket = round(freq)
        now = time.time()

        # Ensure log is up to date.
        self._prune_old_entries(freq_bucket, now)

        if freq_bucket not in self.activity_log or not self.activity_log[freq_bucket]:
            return False  # No activity at all.

        # Calculate total active time from all segments.
        total_active = sum(end - start for start, end in self.activity_log[freq_bucket])

        # Calculate actual time observed (from first segment to now or window limit).
        first_segment_start = self.activity_log[freq_bucket][0][0]
        total_time = min(self.window_sec, now - first_segment_start)

        # Compute duty cycle (active time ratio).
        duty_cycle = total_active / total_time if total_time > 0 else 0.0

        # Get and validate power stats for CV computation.
        stats = self.power_stats[freq_bucket]
        if stats[2] < 10:
            return False  # Not enough samples.

        mean = stats[0] / stats[2]
        variance = (stats[1] - stats[0]**2 / stats[2]) / (stats[2] - 1)
        cv = np.sqrt(variance) / mean if mean > 0 else 0

        # Continuous = high duty cycle + low power variation.
        return duty_cycle > duty_cycle_thresh and cv < cv_thresh
