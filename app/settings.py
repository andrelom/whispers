import yaml

from functools import lru_cache
from dataclasses import dataclass, field


@dataclass
class FFTSettings:
    threshold_db: float
    min_distance_hz: int

@dataclass
class PeakTrackerSettings:
    min_hits: int
    window_sec: int

@dataclass
class Settings:
    driver: str
    band: str
    band_frequencies: dict[str, list[float]]
    iq_sample_rate_hz: int
    rf_gain_db: int
    scan_duration_sec: float
    min_voice_bandwidth_hz: int
    narrowband_sample_rate_hz: int
    narrowband_capture_duration_sec: int
    fft: FFTSettings = field(default_factory=FFTSettings)
    peak_tracker: PeakTrackerSettings = field(default_factory=PeakTrackerSettings)


def _require(config: dict, key: str, expected_type, path="root") -> any:
    if key not in config:
        raise ValueError(f"Missing required setting: '{path}.{key}'")
    value = config[key]
    if not isinstance(value, expected_type):
        raise TypeError(f"Invalid type for '{path}.{key}': expected {expected_type.__name__}, got {type(value).__name__}")
    return value


@lru_cache(maxsize=1)
def get_settings(path: str = "./settings.yaml") -> Settings:
    """
    Load system configuration from a YAML file and validate all required fields.

    Args:
        path (str): Path to the configuration file. Default is './settings.yaml'.

    Returns:
        Settings: Fully parsed and validated configuration object.

    Raises:
        ValueError: If required keys are missing.
        TypeError: If any setting has the wrong type.
    """
    with open(path, "r") as f:
        raw = yaml.safe_load(f) or {}

    # Validate top-level keys.
    driver = _require(raw, "driver", str)
    band = _require(raw, "band", str)
    band_frequencies = _require(raw, "band_frequencies", dict)
    iq_sample_rate_hz = _require(raw, "iq_sample_rate_hz", int)
    rf_gain_db = _require(raw, "rf_gain_db", int)
    scan_duration_sec = _require(raw, "scan_duration_sec", (int, float))
    min_voice_bandwidth_hz = _require(raw, "min_voice_bandwidth_hz", int)
    narrowband_sample_rate_hz = _require(raw, "narrowband_sample_rate_hz", int)
    narrowband_capture_duration_sec = _require(raw, "narrowband_capture_duration_sec", int)

    # Validate FFT settings.
    fft = raw.get("fft", {})
    fft_threshold_db = _require(fft, "threshold_db", (int, float), path="fft")
    fft_min_distance_hz = _require(fft, "min_distance_hz", int, path="fft")

    # Validate Peak Tracker settings.
    peak_tracker = raw.get("peak_tracker", {})
    peak_tracker_min_hits = _require(peak_tracker, "min_hits", int, path="peak_tracker")
    peak_tracker_window_sec = _require(peak_tracker, "window_sec", int, path="peak_tracker")

    return Settings(
        driver=driver,
        band=band,
        band_frequencies=band_frequencies,
        iq_sample_rate_hz=iq_sample_rate_hz,
        rf_gain_db=rf_gain_db,
        scan_duration_sec=scan_duration_sec,
        min_voice_bandwidth_hz=min_voice_bandwidth_hz,
        narrowband_sample_rate_hz=narrowband_sample_rate_hz,
        narrowband_capture_duration_sec=narrowband_capture_duration_sec,
        fft=FFTSettings(
            threshold_db=float(fft_threshold_db),
            min_distance_hz=fft_min_distance_hz,
        ),
        peak_tracker=PeakTrackerSettings(
            min_hits=peak_tracker_min_hits,
            window_sec=peak_tracker_window_sec,
        )
    )
