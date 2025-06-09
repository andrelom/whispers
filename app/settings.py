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
    )
