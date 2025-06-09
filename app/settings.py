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
    scan_duration_sec: int
    min_voice_bandwidth_hz: int
    narrowband_sample_rate_hz: int
    narrowband_capture_duration_sec: int
    fft: FFTSettings = field(default_factory=FFTSettings)
    peak_tracker: PeakTrackerSettings = field(default_factory=PeakTrackerSettings)

@lru_cache(maxsize=1)
def get_settings(path: str = "./settings.toml") -> Settings:
    with open(path, "r") as f:
        raw = yaml.safe_load(f) or {}

    fft = raw.get("fft", {})
    peak_tracker = raw.get("peak_tracker", {})

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
        fft=FFTSettings(**fft),
        peak_tracker=PeakTrackerSettings(**peak_tracker),
    )
