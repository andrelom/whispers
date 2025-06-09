import yaml

from functools import lru_cache
from dataclasses import dataclass


@dataclass
class Settings:
    # SDR driver identifier used by SoapySDR.
    # Examples: airspy, rtlsdr, etc.
    driver: str

    # Frequency band to scan. This selects a predefined list of center
    # frequencies from the band_frequencies section below.
    # Valid options: hf, vhf, uhf, or a custom key defined in band_frequencies.
    band: str

    # List of center frequencies in Hz for each band.
    # Each band maps to a list of center frequencies (in Hz) to scan.
    # These are used sequentially by the scanner.
    band_frequencies: dict[str, list[float]]

    # IQ sample rate of the SDR device in Hz.
    # Higher values provide wider bandwidth but increase CPU load and memory usage.
    iq_sample_rate_hz: int

    # SDR gain setting in decibels.
    # Adjust based on noise floor and dynamic range requirements.
    rf_gain_db: int

    # Duration in seconds to capture each wideband IQ slice.
    # Shorter durations reduce latency, longer ones improve FFT resolution.
    scan_duration_sec: int

    # Minimum bandwidth (in Hz) of a signal to be considered speech-like.
    # Filters out narrow peaks likely to be noise or digital carriers.
    min_voice_bandwidth_hz: int

    # Sample rate of the output narrowband IQ stream in Hz after downconversion.
    # This defines the bandwidth of the captured subband.
    narrowband_sample_rate_hz: int

    # Duration of narrowband IQ capture in seconds (per detected peak).
    # Determines how much post-trigger data is collected.
    narrowband_capture_duration_sec: int

@lru_cache(maxsize=1)
def get_settings(path: str = "./settings.toml") -> Settings:
    with open(path, "r") as f:
        raw = yaml.safe_load(f) or {}

    return Settings(
        driver=raw.get("driver"),
        band=raw.get("band"),
        band_frequencies=raw.get("band_frequencies"),
        iq_sample_rate_hz=raw.get("iq_sample_rate_hz"),
        rf_gain_db=raw.get("rf_gain_db"),
        scan_duration_sec=raw.get("scan_duration_sec"),
        min_voice_bandwidth_hz=raw.get("min_voice_bandwidth_hz"),
        narrowband_sample_rate_hz=raw.get("narrowband_sample_rate_hz"),
        narrowband_capture_duration_sec=raw.get("narrowband_capture_duration_sec"),
    )
