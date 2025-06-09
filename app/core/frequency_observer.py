import time

from collections import deque


class FrequencyObserver:
    """
    Tracks activity patterns on individual frequencies to distinguish speech-like signals
    (bursty, intermittent) from continuous transmissions (FM, music, etc).
    """

    def __init__(self, window_sec=30):
        self.window_sec = window_sec
        self.activity_log = {}

    def update(self, freq: float, power: float):
        now = time.time()
        freq = round(freq)
        log = self.activity_log.setdefault(freq, deque())
        log.append((now, power))

        # Prune old entries.
        while log and now - log[0][0] > self.window_sec:
            log.popleft()

    def is_continuous(self, freq: float, power_threshold_db=-40.0, duty_cycle_thresh=0.8) -> bool:
        """
        Estimate if signal is continuous based on power duty cycle.

        Returns:
            bool: True if the signal is likely continuous.
        """
        freq = round(freq)
        log = self.activity_log.get(freq, deque())

        if not log:
            return False

        powers = [p for _, p in log]
        active_count = sum(1 for p in powers if p > power_threshold_db)
        duty_cycle = active_count / len(powers)

        return duty_cycle > duty_cycle_thresh
