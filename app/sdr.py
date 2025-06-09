import time
import logging

import numpy as np
import SoapySDR

from datetime import datetime, timezone
from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_CF32

from app.settings import Settings
from app.core.queue import AbstractCaptureQueue
from app.core.buffer import CircularIQBuffer
from app.core.fft import FFTProcessor
from app.core.peak_tracker import PeakTracker
from app.core.downconverter import VirtualReceiver
from app.core.frequency_observer import FrequencyObserver
from app.filters.envelope import is_human_like_envelope


logger = logging.getLogger(__name__)


class SDRDevice:
    """
    Represents a physical Software Defined Radio (SDR) device using SoapySDR.

    Handles initialization, tuning, streaming, and sample capture.
    """

    def __init__(self, settings: Settings):
        """
        Initialize the SDRDevice with configuration settings.

        Args:
            settings (Settings): Global configuration loaded from YAML/TOML.
        """
        self.driver = settings.driver
        self.iq_sample_rate_hz = settings.iq_sample_rate_hz
        self.rf_gain_db = settings.rf_gain_db

        self.device = None
        self.stream = None
        self.center_frequency = 0.0

    def initialize(self):
        """
        Connect and configure the SDR hardware.
        Sets sample rate and RF gain.
        """
        self.device = SoapySDR.Device({"driver": self.driver})
        self.device.setSampleRate(SOAPY_SDR_RX, 0, self.iq_sample_rate_hz)
        self.device.setGain(SOAPY_SDR_RX, 0, self.rf_gain_db)
        logger.info(f"SDR device initialized.")

    def tune(self, frequency):
        """
        Tune the SDR to a given center frequency.

        Args:
            frequency (float): Frequency in Hz.
        """
        self.center_frequency = frequency
        self.device.setFrequency(SOAPY_SDR_RX, 0, frequency)

    def start_stream(self):
        """
        Start the SDR streaming if not already active.
        """
        if self.stream:
            return
        self.stream = self.device.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
        self.device.activateStream(self.stream)

    def stop_stream(self):
        """
        Stop and clean up the SDR stream.
        """
        if not self.stream:
            return
        self.device.deactivateStream(self.stream)
        self.device.closeStream(self.stream)
        self.stream = None

    def capture_samples(self, num_samples):
        """
        Capture a block of IQ samples from the SDR.

        Args:
            num_samples (int): Number of complex samples to capture.

        Returns:
            np.ndarray: Captured IQ samples as complex64.
        """
        buffer = np.empty(num_samples, dtype=np.complex64)
        received = 0
        while received < num_samples:
            sr = self.device.readStream(self.stream, [buffer[received:]], num_samples - received)
            if sr.ret > 0:
                received += sr.ret
            elif sr.ret < 0:
                raise IOError(f"SDR read error: {sr.ret}")
        return buffer

    def close(self):
        """
        Safely shut down the SDR device and release resources.
        """
        if self.stream:
            self.stop_stream()
        if self.device:
            self.device.close()
            self.device = None
        logger.info("SDR device closed.")


class WidebandScanner:
    """
    Controls wideband scanning over a range of center frequencies.

    This class captures wideband IQ data, performs FFT-based peak detection, tracks
    stable spectral peaks, and extracts narrowband signals using virtual receivers.
    """

    def __init__(self, sdr_device: SDRDevice, capture_queue: AbstractCaptureQueue, settings: Settings):
        """
        Initialize the scanner with SDR device, queue, and configuration.

        Args:
            sdr_device (SDRDevice): The SDR device abstraction.
            capture_queue (AbstractCaptureQueue): Queue for storing valid signal captures.
            settings (Settings): Global settings object with frequency plan and scanning parameters.
        """
        self.sdr_device = sdr_device
        self.capture_queue = capture_queue

        # Band settings.
        self.band = settings.band
        self.band_frequencies = settings.band_frequencies

        # Scan and capture timing.
        self.scan_duration_sec = settings.scan_duration_sec
        self.narrowband_capture_duration_sec = settings.narrowband_capture_duration_sec

        # Signal characteristics.
        self.min_voice_bandwidth_hz = settings.min_voice_bandwidth_hz
        self.narrowband_sample_rate_hz = settings.narrowband_sample_rate_hz

        # FFT detection thresholds.
        self.fft_threshold_db = settings.fft.threshold_db
        self.fft_min_distance_hz = settings.fft.min_distance_hz

        # Peak stability tracker settings.
        self.peak_min_hits = settings.peak_tracker.min_hits
        self.peak_window_sec = settings.peak_tracker.window_sec

        # Internal runtime state.
        self.running = False
        self.center_buffers = {}  # Dict[float, CircularIQBuffer].
        self.last_center_freq = None

        # Signal processors.
        self.fft = FFTProcessor(self.sdr_device.iq_sample_rate_hz, self.fft_threshold_db, self.fft_min_distance_hz)
        self.peak_tracker = PeakTracker(min_hits=self.peak_min_hits, window_sec=self.peak_window_sec)
        self.freq_observer = FrequencyObserver(window_sec=30)

    def start(self):
        """
        Start scanning loop. For each configured center frequency:
        - Tune SDR
        - Capture IQ data
        - Extract and track peaks
        - Submit narrowband speech-like signals to capture queue
        """
        self.running = True
        self.sdr_device.initialize()
        sample_rate = int(self.sdr_device.iq_sample_rate_hz)
        band_centers = self.get_band_centers()

        try:
            while self.running:
                for center_freq in band_centers:
                    if not self.running:
                        break

                    # Initialize new buffer if changing center frequency.
                    if center_freq != self.last_center_freq:
                        self._init_center_frequency(center_freq)

                    logger.debug(f"Scanning center frequency {center_freq:.0f} Hz")
                    self.sdr_device.tune(center_freq)
                    self.sdr_device.start_stream()

                    # Capture wideband IQ data.
                    num_samples = int(sample_rate * self.scan_duration_sec)
                    start_time = time.perf_counter()
                    iq_block = self.sdr_device.capture_samples(num_samples)

                    self._handle_center_iq_block(center_freq, iq_block)

                    # Ensure fixed scan duration.
                    elapsed = time.perf_counter() - start_time
                    time.sleep(max(0, self.scan_duration_sec - elapsed))

                    self.sdr_device.stop_stream()
        except Exception as e:
            logger.exception(f"Scanner error: {e}")
        finally:
            self.stop()

    def _init_center_frequency(self, center_freq: float):
        """
        Allocate and reset buffer state for a newly tuned center frequency.

        Args:
            center_freq (float): Frequency in Hz.
        """
        self.center_buffers[center_freq] = CircularIQBuffer(
            sample_rate=self.sdr_device.iq_sample_rate_hz,
            duration_sec=max(30.0, self.narrowband_capture_duration_sec * 2)
        )
        self.last_center_freq = center_freq
        logger.debug(f"Initialized buffer for center frequency: {center_freq:.0f} Hz")

    def _handle_center_iq_block(self, center_freq: float, iq_block: np.ndarray):
        """
        Process a captured wideband IQ block:
        - Perform FFT and extract peaks
        - Filter by bandwidth
        - Track and confirm stable signals
        - Pass valid peaks to capture processor

        Args:
            center_freq (float): Center frequency of the current scan window.
            iq_block (np.ndarray): Raw wideband complex64 samples.
        """
        # Append to rolling buffer.
        self.center_buffers[center_freq].append(iq_block)

        # Extract peak regions.
        regions = self.fft.extract_peak_regions(iq_block)
        filtered = [r for r in regions if r["bandwidth"] >= self.min_voice_bandwidth_hz]
        stable = self.peak_tracker.update_and_filter(filtered)

        if not stable:
            logger.debug("No stable peaks detected.")
            return

        logger.debug(f"Detected {len(stable)} stable peak(s):")
        for region in stable:
            self.freq_observer.update(region["frequency"], region["power_db"])
            logger.debug(f"  - Freq: {region['frequency']:.0f} Hz | "
                         f"Power: {region['power_db']:.1f} dB | "
                         f"BW: {region['bandwidth']:.0f} Hz")
            self._process_detected_peak(center_freq, region)

    def _process_detected_peak(self, center_freq: float, region: dict):
        """
        Process a single detected peak:
        - Validate it's not a continuous carrier
        - Extract narrowband subband
        - Check for speech-like envelope
        - Queue valid captures

        Args:
            center_freq (float): Wideband center frequency.
            region (dict): Region dict with 'frequency', 'power_db', 'bandwidth'.
        """
        signal_freq = region["frequency"]

        if self.freq_observer.is_continuous(signal_freq):
            logger.debug(f"Rejected {signal_freq:.0f} Hz: continuous signal")
            return

        try:
            wide_iq = self.center_buffers[center_freq].extract_recent(self.narrowband_capture_duration_sec)
        except ValueError as e:
            logger.warning(f"Buffer error for {signal_freq:.0f} Hz: {e}")
            return

        receiver = VirtualReceiver(
            center_freq=center_freq,
            target_freq=signal_freq,
            input_sample_rate=self.sdr_device.iq_sample_rate_hz,
            output_sample_rate=self.narrowband_sample_rate_hz
        )
        narrow_iq = receiver.extract_subband(wide_iq)

        if not is_human_like_envelope(narrow_iq, self.narrowband_sample_rate_hz):
            logger.debug(f"Rejected {signal_freq:.0f} Hz: non-human envelope")
            return

        # Package and enqueue the capture.
        capture = {
            "center_frequency": center_freq,
            "signal_frequency": signal_freq,
            "power_db": region["power_db"],
            "bandwidth": region["bandwidth"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sample_rate": self.narrowband_sample_rate_hz,
            "iq_data": narrow_iq,
        }
        self.capture_queue.put(capture)
        logger.info(f"Captured signal at {signal_freq:.0f} Hz")

    def stop(self):
        """
        Stop scanning and clean up internal resources.
        """
        if not self.running:
            return
        self.running = False
        self.sdr_device.close()
        self.center_buffers.clear()
        self.peak_tracker.clear()

    def get_band_centers(self) -> list[float]:
        """
        Return the configured list of center frequencies for the selected band.

        Returns:
            list[float]: Center frequencies (Hz) to scan.
        """
        return self.band_frequencies.get(self.band, [self.sdr_device.center_frequency])
