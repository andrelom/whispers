import numpy as np
import scipy.signal


class VirtualReceiver:
    """
    VirtualReceiver extracts a narrowband signal from a wideband IQ stream using
    digital downconversion (frequency shifting and decimation).

    This avoids the need to physically retune the SDR. Instead, it digitally shifts
    the desired frequency to baseband (0 Hz) and reduces the sample rate to isolate
    the signal of interest.

    Attributes:
        freq_offset (float): Frequency shift to bring target to baseband.
        input_sample_rate (float): Original sample rate of wideband IQ data.
        output_sample_rate (float): Desired sample rate for narrowband output.
        decimation_factor (int): Integer factor by which to reduce the sample rate.
    """

    def __init__(
        self,
        center_freq: float,
        target_freq: float,
        input_sample_rate: float,
        output_sample_rate: float
    ):
        """
        Initialize the virtual receiver.

        Args:
            center_freq (float): The current center frequency of the SDR (Hz).
            target_freq (float): The frequency of the signal to extract (Hz).
            input_sample_rate (float): Sample rate of the wideband IQ stream (Hz).
            output_sample_rate (float): Desired narrowband sample rate (Hz).
        """
        self.freq_offset = target_freq - center_freq
        self.input_sample_rate = input_sample_rate
        self.output_sample_rate = output_sample_rate
        if output_sample_rate >= input_sample_rate:
            raise ValueError("Output sample rate must be lower than input sample rate.")
        self.decimation_factor = int(input_sample_rate // output_sample_rate)

    def extract_subband(self, iq_block: np.ndarray) -> np.ndarray:
        """
        Perform digital downconversion to isolate the signal near target_freq.

        This includes:
        1. Mixing (frequency shift): Brings target signal to baseband (0 Hz).
        2. Decimation (downsampling): Reduces bandwidth and sample rate.

        Args:
            iq_block (np.ndarray): Wideband IQ block (complex64 array).

        Returns:
            np.ndarray: Narrowband IQ stream centered at 0 Hz, complex64.
        """
        n = len(iq_block)

        # Generate time vector in seconds.
        t = np.arange(n) / self.input_sample_rate

        # Mix (shift) the target frequency to 0 Hz.
        mixed = iq_block * np.exp(-1j * 2 * np.pi * self.freq_offset * t)

        # Decimate to reduce bandwidth (and data size).
        filtered = scipy.signal.decimate(mixed, self.decimation_factor, ftype='fir', zero_phase=True)

        return filtered.astype(np.complex64)
