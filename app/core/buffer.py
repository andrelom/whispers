import numpy as np


class CircularIQBuffer:
    """
    Circular buffer to store complex IQ samples with efficient support for overwrite,
    wrap-around handling, and recent-data extraction.

    Suitable for high-throughput SDR (Software Defined Radio) applications where continuous
    data streams must be buffered for retrospective access or processing.
    """

    def __init__(self, sample_rate: float, duration_sec: float = 30.0):
        """
        Initialize the buffer with a fixed duration and sampling rate.

        Args:
            sample_rate (float): Samples per second (Hz).
            duration_sec (float): Total duration of buffer storage in seconds.
        """
        self.sample_rate = int(sample_rate)
        self.buffer_size = int(self.sample_rate * duration_sec)

        # Allocate zero-filled complex buffer.
        self.buffer = np.zeros(self.buffer_size, dtype=np.complex64)

        # Points to the write head (wraps around).
        self.write_pos = 0

        # Number of valid samples currently stored.
        self.available = 0

    def append(self, iq_block: np.ndarray):
        """
        Append a new block of IQ samples into the buffer.

        Oldest samples are overwritten if buffer overflows.

        Args:
            iq_block (np.ndarray): Complex64 numpy array of new samples.
        """
        n = len(iq_block)
        if n == 0:
            return

        # If block is larger than buffer, keep only the most recent part.
        if n > self.buffer_size:
            iq_block = iq_block[-self.buffer_size:]
            n = self.buffer_size
            self.available = self.buffer_size
            self.write_pos = 0

        # Compute where new data will start writing.
        start_pos = (self.write_pos + self.available) % self.buffer_size
        end_pos = (start_pos + n) % self.buffer_size

        # Case 1: Data fits without wrapping.
        if start_pos + n <= self.buffer_size:
            self.buffer[start_pos:start_pos + n] = iq_block
        # Case 2: Data wraps around to beginning.
        else:
            first_part = self.buffer_size - start_pos
            second_part = n - first_part
            self.buffer[start_pos:] = iq_block[:first_part]
            self.buffer[:second_part] = iq_block[first_part:]

        # Update buffer state.
        self.available = min(self.available + n, self.buffer_size)
        self.write_pos = end_pos

    def extract_recent(self, duration_sec: float) -> np.ndarray:
        """
        Extract the most recent samples from the buffer.

        Args:
            duration_sec (float): How many seconds of samples to extract.

        Returns:
            np.ndarray: Complex64 array of recent samples.
        """
        # Determine how many samples to extract.
        n = min(
            int(self.sample_rate * duration_sec),
            self.available
        )

        if n <= 0:
            return np.array([], dtype=np.complex64)

        # Calculate the start position of the desired window.
        start_pos = (self.write_pos + self.available - n) % self.buffer_size

        # Case 1: Data is contiguous.
        if start_pos + n <= self.buffer_size:
            return self.buffer[start_pos:start_pos + n].copy()

        # Case 2: Data wraps around.
        first_part = self.buffer_size - start_pos
        second_part = n - first_part
        return np.concatenate([
            self.buffer[start_pos:],
            self.buffer[:second_part]
        ])

    def clear(self):
        """
        Clear the buffer content and reset state.
        """
        self.buffer[:] = 0
        self.write_pos = 0
        self.available = 0
