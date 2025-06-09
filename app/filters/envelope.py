import numpy as np
import scipy.signal


def is_human_like_envelope(
    iq_data: np.ndarray,
    sample_rate: int,
    threshold: float = 0.3,
    cutoff_hz: int = 20
) -> bool:
    """
    Analyzes the amplitude envelope of the IQ signal to detect bursty/speech-like behavior.

    Args:
        iq_data (np.ndarray): Complex64 narrowband IQ samples.
        sample_rate (int): Sample rate in Hz.
        threshold (float): CV threshold for envelope variability (speech ≈ 0.3-0.6).
        cutoff_hz (int): Low-pass filter cutoff for envelope smoothing (speech ~2-20 Hz).

    Returns:
        bool: True if the signal shows speech-like envelope characteristics.
    """

    # Step 1: Compute the instantaneous amplitude (envelope proxy) from IQ samples.
    power = np.abs(iq_data)

    # Step 2: Apply a low-pass Butterworth filter to smooth the envelope.
    # This preserves low-frequency modulation typical of human speech (~2-20 Hz).
    sos = scipy.signal.butter(4, cutoff_hz, 'lowpass', fs=sample_rate, output='sos')
    envelope = scipy.signal.sosfiltfilt(sos, power)

    # Step 3: Check for near-silence or zero signal.
    # If the mean envelope is extremely low, reject early (avoids false positives on noise).
    mean_env = np.mean(envelope)
    if mean_env < 1e-8:
        return False

    # Step 4: Calculate the coefficient of variation (CV).
    # This normalizes the envelope's standard deviation by its mean, making it gain-independent.
    cv = np.std(envelope) / mean_env

    # Step 5: Compute peak-to-average ratio (PAR).
    # Human speech has bursts of energy (high peaks), while continuous tones are flatter.
    peak_to_avg = np.max(envelope) / mean_env

    # Step 6: Classify as speech-like if both metrics indicate bursty modulation.
    return (cv > threshold) and (peak_to_avg > 1.5)
