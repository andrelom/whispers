import numpy as np
import scipy.signal


def is_human_like_envelope(iq_data: np.ndarray, sample_rate: int, threshold: float = 0.5) -> bool:
    """
    Analyzes the amplitude envelope of the IQ signal to detect bursty/speech-like behavior.

    Args:
        iq_data (np.ndarray): Complex64 narrowband IQ samples.
        sample_rate (int): Sample rate in Hz.
        threshold (float): Stddev threshold for "bursty" activity.

    Returns:
        bool: True if envelope activity looks like human speech.
    """
    power = np.abs(iq_data)
    envelope = scipy.signal.medfilt(power, kernel_size=201)
    std_dev = np.std(envelope)
    return std_dev > threshold
