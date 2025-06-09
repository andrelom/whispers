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

    def __del__(self):
        """
        Destructor to ensure the SDR device is properly closed.
        """
        self.close()


class WidebandScanner:
    """
    Controls wideband scanning over a range of center frequencies.

    Captures IQ data, performs FFT-based peak detection, tracks stable signals,
    and extracts narrowband captures around those signals using virtual receivers.
    """

    def __init__(self, sdr_device: SDRDevice, capture_queue: AbstractCaptureQueue, settings: Settings):
        """
        Initialize the scanning system and its parameters.

        Args:
            sdr_device (SDRDevice): Physical SDR device wrapper.
            capture_queue (AbstractCaptureQueue): Queue to store output captures.
            settings (Settings): Loaded configuration object.
        """
        self.sdr_device = sdr_device
        self.capture_queue = capture_queue

        self.band = settings.band
        self.band_frequencies = settings.band_frequencies
        self.scan_duration_sec = settings.scan_duration_sec
        self.min_voice_bandwidth_hz = settings.min_voice_bandwidth_hz
        self.narrowband_sample_rate_hz = settings.narrowband_sample_rate_hz
        self.narrowband_capture_duration_sec = settings.narrowband_capture_duration_sec

        self.fft_threshold_db = settings.fft.threshold_db
        self.fft_min_distance_hz = settings.fft.min_distance_hz

        self.peak_min_hits = settings.peak_tracker.min_hits
        self.peak_window_sec = settings.peak_tracker.window_sec

        self.running = False
        self.circular_buffer = CircularIQBuffer(sample_rate=self.sdr_device.iq_sample_rate_hz, duration_sec=30.0)
        self.fft = FFTProcessor(self.sdr_device.iq_sample_rate_hz, self.fft_threshold_db, self.fft_min_distance_hz)
        self.peak_tracker = PeakTracker(min_hits=self.peak_min_hits, window_sec=self.peak_window_sec)

    def start(self):
        """
        Begin scanning loop over all configured center frequencies.

        Captures wideband IQ, tracks signal activity, and dispatches narrowband subbands to queue.
        """
        self.running = True
        self.sdr_device.initialize()
        sample_rate = int(self.sdr_device.iq_sample_rate_hz)
        num_samples = int(sample_rate * self.scan_duration_sec)
        band_centers = self.get_band_centers()
        try:
            while self.running:
                for freq in band_centers:
                    logger.debug(f"Scanning center frequency {freq:.0f} Hz")
                    self.sdr_device.tune(freq)
                    self.sdr_device.start_stream()
                    start = time.perf_counter()
                    iq_block = self.sdr_device.capture_samples(num_samples)
                    self.circular_buffer.append(iq_block)
                    self.handle_iq_block(iq_block)
                    elapsed = time.perf_counter() - start
                    if elapsed < self.scan_duration_sec:
                        time.sleep(self.scan_duration_sec - elapsed)
                    self.sdr_device.stop_stream()
        except Exception as e:
            logger.error(f"Error starting wideband scanner: {e}")
        finally:
            self.stop()

    def stop(self):
        """
        Stop scanning and clean up all internal state.
        """
        self.sdr_device.close()
        self.circular_buffer.clear()
        self.peak_tracker.clear()
        self.running = False

    def get_band_centers(self):
        """
        Get the list of center frequencies for the selected band.

        Returns:
            list[float]: Frequencies in Hz.
        """
        return self.band_frequencies.get(self.band, [self.sdr_device.center_frequency])

    def handle_iq_block(self, iq_block: np.ndarray):
        """
        Process a captured IQ block: perform FFT, filter peaks, track stability, capture stable signals.

        Args:
            iq_block (np.ndarray): Complex IQ samples.
        """
        regions = self.fft.extract_peak_regions(iq_block)
        filtered = [r for r in regions if r["bandwidth"] >= self.min_voice_bandwidth_hz]
        stable = self.peak_tracker.update_and_filter(filtered)
        if stable:
            logger.debug(f"Total of {len(stable)} stable region(s) confirmed:")
            for region in stable:
                logger.debug(f"  - Freq: {region['frequency']:.0f} Hz | Power: {region['power_db']:.1f} dB | BW ~{region['bandwidth']:.0f} Hz")
                result = self.capture_peak_region(region)
                self.capture_queue.put(result)
        else:
            logger.debug("No stable peaks detected.")

    def capture_peak_region(self, region: dict) -> dict:
        """
        Extract a narrowband capture centered around a stable detected signal.

        Args:
            region (dict): Dictionary with 'frequency', 'power_db', 'bandwidth'.

        Returns:
            dict: Capture metadata and IQ data.
        """
        target_freq = region["frequency"]
        logger.debug(f"Capturing virtual receiver IQ at {target_freq:.0f} Hz")
        center_freq = self.sdr_device.center_frequency
        try:
            wide_iq = self.circular_buffer.extract_recent(self.narrowband_capture_duration_sec)
        except ValueError:
            logger.warning("Insufficient IQ data in buffer, skipping capture.")
            return {}
        receiver = VirtualReceiver(
            center_freq=center_freq,
            target_freq=target_freq,
            input_sample_rate=self.sdr_device.iq_sample_rate_hz,
            output_sample_rate=self.narrowband_sample_rate_hz
        )
        narrow_iq = receiver.extract_subband(wide_iq)
        return {
            "frequency": target_freq,
            "power_db": region["power_db"],
            "bandwidth": region["bandwidth"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sample_rate": self.narrowband_sample_rate,
            "iq_data": narrow_iq
        }

    def get_queue(self):
        """
        Returns the queue where captures are being placed.

        Returns:
            AbstractCaptureQueue: Capture queue used for downstream processing.
        """
        return self.capture_queue
