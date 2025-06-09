import numpy as np


class CircularIQBuffer:
    """
    Circular (ring) buffer for storing IQ samples in memory.

    This buffer is designed to continuously hold the most recent window of IQ data,
    enabling retrospective access to past samples. It's especially useful when performing
    signal detection on streaming data, where you want to "go back in time" and extract
    a segment centered on a detected event (e.g., voice signal).

    Attributes:
        sample_rate (int): Number of IQ samples per second (Hz).
        buffer_size (int): Total number of complex samples stored.
        buffer (np.ndarray): Internal memory array for IQ data.
        write_pos (int): Current write position (wraps around).
        is_full (bool): Indicates if the buffer has wrapped at least once.
    """

    def __init__(self, sample_rate: float, duration_sec: float = 30.0):
        """
        Initialize the circular buffer.

        Args:
            sample_rate (float): IQ sample rate in Hz.
            duration_sec (float): Total duration (in seconds) of IQ data to retain.
        """
        self.sample_rate = int(sample_rate)
        self.buffer_size = int(self.sample_rate * duration_sec)
        self.buffer = np.zeros(self.buffer_size, dtype=np.complex64)
        self.write_pos = 0
        self.is_full = False

    def append(self, iq_block: np.ndarray):
        """
        Append a new block of IQ samples to the buffer.

        Args:
            iq_block (np.ndarray): Array of complex64 IQ samples to store.
        """
        n = len(iq_block)
        end_pos = self.write_pos + n

        if end_pos <= self.buffer_size:
            # Fits without wrapping.
            self.buffer[self.write_pos:end_pos] = iq_block
        else:
            # Wraps around end of buffer.
            first_part = self.buffer_size - self.write_pos
            self.buffer[self.write_pos:] = iq_block[:first_part]
            self.buffer[:n - first_part] = iq_block[first_part:]

        self.write_pos = (self.write_pos + n) % self.buffer_size

        # Mark buffer as "full" after one full cycle.
        if not self.is_full and self.write_pos == 0:
            self.is_full = True

    def extract_recent(self, duration_sec: float) -> np.ndarray:
        """
        Extract the most recent IQ samples from the buffer.

        Args:
            duration_sec (float): Duration (in seconds) of samples to retrieve.

        Returns:
            np.ndarray: Complex64 array of IQ data, most recent first.

        Raises:
            ValueError: If not enough data has been buffered yet.
        """
        n = int(self.sample_rate * duration_sec)

        if not self.is_full and self.write_pos < n:
            raise ValueError("Not enough data in buffer yet")

        start_pos = (self.write_pos - n) % self.buffer_size

        if start_pos + n <= self.buffer_size:
            # Continuous block.
            return np.copy(self.buffer[start_pos:start_pos + n])
        else:
            # Wrapped block: needs stitching from end and beginning.
            first_part = self.buffer_size - start_pos
            return np.concatenate([
                self.buffer[start_pos:],
                self.buffer[:n - first_part]
            ])

    def clear(self):
        """
        Clear the buffer contents and reset the write position.
        """
        self.buffer[:] = 0
        self.write_pos = 0
        self.is_full = False
