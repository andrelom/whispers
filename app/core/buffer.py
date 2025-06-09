import numpy as np


class CircularIQBuffer:
    def __init__(self, sample_rate: float, duration_sec: float = 30.0):
        self.sample_rate = int(sample_rate)
        self.buffer_size = int(self.sample_rate * duration_sec)
        self.buffer = np.zeros(self.buffer_size, dtype=np.complex64)
        self.write_pos = 0
        self.is_full = False

    def append(self, iq_block: np.ndarray):
        n = len(iq_block)
        end_pos = self.write_pos + n
        if end_pos <= self.buffer_size:
            self.buffer[self.write_pos:end_pos] = iq_block
        else:
            first_part = self.buffer_size - self.write_pos
            self.buffer[self.write_pos:] = iq_block[:first_part]
            self.buffer[:n - first_part] = iq_block[first_part:]
        self.write_pos = (self.write_pos + n) % self.buffer_size
        if not self.is_full and self.write_pos == 0:
            self.is_full = True

    def extract_recent(self, duration_sec: float) -> np.ndarray:
        n = int(self.sample_rate * duration_sec)
        if not self.is_full and self.write_pos < n:
            raise ValueError("Not enough data in buffer yet")
        start_pos = (self.write_pos - n) % self.buffer_size
        if start_pos + n <= self.buffer_size:
            return np.copy(self.buffer[start_pos:start_pos + n])
        else:
            first_part = self.buffer_size - start_pos
            return np.concatenate([
                self.buffer[start_pos:],
                self.buffer[:n - first_part]
            ])

    def clear(self):
        self.buffer[:] = 0
        self.write_pos = 0
        self.is_full = False
