import time

from collections import defaultdict


class PeakTracker:
    def __init__(self, min_hits=3, window_sec=10):
        self.min_hits = min_hits
        self.window_sec = window_sec
        self.history = defaultdict(list)

    def update_and_filter(self, detected_peaks: list[dict]) -> list[dict]:
        now = time.time()
        stable_peaks = []
        for peak in detected_peaks:
            freq = round(peak["frequency"])
            self.history[freq].append(now)

        for freq, timestamps in list(self.history.items()):
            self.history[freq] = [t for t in timestamps if now - t <= self.window_sec]
            if not self.history[freq]:
                del self.history[freq]
                continue
            if len(self.history[freq]) >= self.min_hits:
                for peak in detected_peaks:
                    if round(peak["frequency"]) == freq:
                        stable_peaks.append(peak)
                        break
        return stable_peaks

    def clear(self):
        self.history.clear()
