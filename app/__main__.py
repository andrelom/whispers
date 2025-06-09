import logging
import time

from app.settings import get_settings
from app.sdr import SDRDevice, WidebandScanner
from app.core.queue import InMemoryCaptureQueue


logger = logging.getLogger(__name__)


def main():
    logger.info("Starting Whispers SDR pipeline...")

    # Load settings.
    settings = get_settings()

    # Setup SDR and queue.
    sdr_device = SDRDevice(settings)
    capture_queue = InMemoryCaptureQueue()

    # Setup wideband scanner.
    scanner = WidebandScanner(sdr_device, capture_queue, settings)

    try:
        scanner.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, stopping scanner...")
        scanner.stop()
    except Exception as e:
        logger.exception(f"Unexpected error occurred: {e}")
    finally:
        logger.info("Scanner shutdown complete.")

        # Optional: Drain the queue (example).
        while not capture_queue.empty():
            result = capture_queue.get()
            logger.info(f"Captured: {result.get('frequency', '?')} Hz, "
                        f"Power: {result.get('power_db', '?'):.1f} dB, "
                        f"Bandwidth: {result.get('bandwidth', '?')} Hz")


if __name__ == "__main__":
    main()
