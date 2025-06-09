import numpy as np
import scipy.signal


class VirtualReceiver:
    """
    Extracts a narrowband sub-channel from a wideband IQ stream using digital downconversion,
    anti-aliasing filtering, and resampling. Suitable for use in SDR applications where
    multiple virtual receivers operate on a shared wideband buffer.
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
            center_freq (float): The center frequency of the wideband IQ data (Hz).
            target_freq (float): The frequency to tune to within the wideband signal (Hz).
            input_sample_rate (float): The sample rate of the wideband IQ stream (Hz).
            output_sample_rate (float): The desired output sample rate for the subband (Hz).
        """
        # Frequency offset between the desired subband and the wideband center.
        self.freq_offset = target_freq - center_freq

        self.input_sample_rate = input_sample_rate
        self.output_sample_rate = output_sample_rate

        # Compute decimation factor (must be >= 1 for downsampling).
        self.decimation_factor = input_sample_rate / output_sample_rate

        # Validate that we're not attempting to upsample.
        if self.decimation_factor < 1:
            raise ValueError("Output sample rate must be lower than input sample rate")

        # Design a low-pass FIR filter to suppress aliasing before decimation.
        nyquist = output_sample_rate / 2  # Output Nyquist frequency.
        self.taps = scipy.signal.firwin(
            numtaps=101,                # Filter length (number of taps).
            cutoff=0.9 * nyquist,       # Cutoff frequency with 10% guard band.
            fs=input_sample_rate        # Filter is defined in terms of input sample rate.
        )

    def extract_subband(self, iq_block: np.ndarray) -> np.ndarray:
        """
        Extract and downconvert a narrowband signal centered at the target frequency.

        Args:
            iq_block (np.ndarray): Input wideband complex IQ samples.

        Returns:
            np.ndarray: Downconverted and resampled narrowband complex IQ samples.
        """
        n = len(iq_block)

        # Step 1: Mix (frequency shift) to baseband using a complex exponential.
        phase = 2 * np.pi * self.freq_offset / self.input_sample_rate
        mixer = np.exp(-1j * phase * np.arange(n))  # Efficient phase accumulator.
        mixed = iq_block * mixer  # Shift target frequency to 0 Hz.

        # Step 2: Apply anti-aliasing FIR filter before resampling.
        filtered = scipy.signal.lfilter(self.taps, 1.0, mixed)

        # Step 3: Perform rational resampling to convert to output sample rate.
        resampled = scipy.signal.resample_poly(
            filtered,
            up=1,
            down=int(np.round(self.decimation_factor)),  # Integer approximation of decimation.
            window=('kaiser', 5.0)  # Kaiser window improves stopband performance.
        )

        # Return result as complex64 for memory efficiency and SDR compatibility.
        return resampled.astype(np.complex64)
