import time
import signal
import threading
import logging

from app.settings import get_settings
from app.sdr import SDRDevice, WidebandScanner
from app.core.queue import InMemoryCaptureQueue


logger = logging.getLogger(__name__)

# Global event to coordinate shutdown.
shutdown_event = threading.Event()


def handle_signal(signum, frame):
    logger.info(f"Signal {signum} received, shutting down...")
    shutdown_event.set()


def main():
    logger.info("Starting Whispers SDR pipeline...")

    # Register signal handlers for SIGINT (Ctrl+C), SIGTERM (docker stop).
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Load settings.
    settings = get_settings()

    # Setup SDR and queue.
    sdr_device = SDRDevice(settings)
    capture_queue = InMemoryCaptureQueue()

    # Setup wideband scanner.
    scanner = WidebandScanner(sdr_device, capture_queue, settings)

    try:
        # Run scanner in thread so it can be stopped cleanly.
        thread = threading.Thread(target=scanner.start)
        thread.start()

        # Wait for shutdown signal.
        while not shutdown_event.is_set():
            if not thread.is_alive():
                logger.error("Scanner thread exited unexpectedly.")
                shutdown_event.set()
            time.sleep(0.5)

        logger.info("Shutdown event set, stopping scanner...")
        scanner.stop()
        thread.join()

    except Exception as e:
        logger.exception(f"Unexpected error occurred: {e}")
    finally:
        logger.info("Scanner shutdown complete.")

        # Optional: Drain the queue (example).
        while not capture_queue.empty():
            result = capture_queue.get()
            logger.info(f"Captured: {result.get('signal_frequency', '?')} Hz, "
                        f"Power: {result.get('power_db', '?'):.1f} dB, "
                        f"Bandwidth: {result.get('bandwidth', '?')} Hz")


if __name__ == "__main__":
    main()
