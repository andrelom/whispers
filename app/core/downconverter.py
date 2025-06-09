import numpy as np

import scipy.signal


class VirtualReceiver:
    def __init__(self, center_freq: float, target_freq: float, input_sample_rate: float, output_sample_rate: float):
        self.freq_offset = target_freq - center_freq
        self.input_sample_rate = input_sample_rate
        self.output_sample_rate = output_sample_rate
        self.decimation_factor = int(input_sample_rate // output_sample_rate)

    def extract_subband(self, iq_block: np.ndarray) -> np.ndarray:
        n = len(iq_block)
        t = np.arange(n) / self.input_sample_rate
        mixed = iq_block * np.exp(-1j * 2 * np.pi * self.freq_offset * t)
        filtered = scipy.signal.decimate(mixed, self.decimation_factor, ftype='fir', zero_phase=True)
        return filtered.astype(np.complex64)
