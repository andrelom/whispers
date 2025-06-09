import logging

import numpy as np
import SoapySDR

from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_CF32
from app.settings import Settings


logger = logging.getLogger(__name__)


class SDRDevice:
    def __init__(self, settings: Settings):
        self.driver = settings.driver
        self.iq_sample_rate = settings.iq_sample_rate
        self.rf_gain_db = settings.rf_gain_db

        self.device = None
        self.stream = None
        self.center_frequency = 0.0

    def initialize(self):
        self.device = SoapySDR.Device({"driver": self.driver})
        self.device.setSampleRate(SOAPY_SDR_RX, 0, self.iq_sample_rate)
        self.device.setGain(SOAPY_SDR_RX, 0, self.rf_gain_db)

    def tune(self, frequency):
        self.center_frequency = frequency
        self.device.setFrequency(SOAPY_SDR_RX, 0, frequency)

    def start_stream(self):
        if self.stream:
            return
        self.stream = self.device.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
        self.device.activateStream(self.stream)

    def stop_stream(self):
        if not self.stream:
            return
        self.device.deactivateStream(self.stream)
        self.device.closeStream(self.stream)
        self.stream = None

    def capture_samples(self, num_samples):
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
        if self.stream:
            self.stop_stream()
        if self.device:
            self.device.close()
            self.device = None
        logger.info("SDR device closed.")

    def __del__(self):
        self.close()
