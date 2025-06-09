import abc
import queue


class AbstractCaptureQueue(abc.ABC):
    """
    Abstract base class for a queue that stores narrowband IQ captures.

    This abstraction allows the system to work with different queue implementations,
    such as in-memory queues, disk-backed queues, Redis, or custom transport layers.

    Any concrete subclass must implement the standard queue interface:
    - put(item): enqueue a capture
    - get(): dequeue a capture
    - empty(): check if queue is empty
    """

    @abc.abstractmethod
    def put(self, item: dict):
        """
        Add a capture result to the queue.

        Args:
            item (dict): The narrowband capture dictionary, typically including:
                - frequency (float)
                - power_db (float)
                - bandwidth (float)
                - timestamp (str, ISO format)
                - sample_rate (int)
                - iq_data (np.ndarray or serialized form)
        """
        pass

    @abc.abstractmethod
    def get(self) -> dict:
        """
        Remove and return the next capture from the queue.

        Returns:
            dict: The next narrowband capture.
        """
        pass

    @abc.abstractmethod
    def empty(self) -> bool:
        """
        Check whether the queue is currently empty.

        Returns:
            bool: True if queue has no items.
        """
        pass


class InMemoryCaptureQueue(AbstractCaptureQueue):
    """
    A simple in-memory FIFO queue for capture results using Python's queue.Queue.

    This implementation is suitable for local testing, prototyping, or synchronous pipelines.
    It is not suitable for multi-process or distributed deployments.
    """

    def __init__(self):
        """
        Initialize the in-memory queue.
        """
        self._queue = queue.Queue()

    def put(self, item: dict):
        """
        Enqueue a capture result.

        Args:
            item (dict): The capture result dictionary.
        """
        self._queue.put(item)

    def get(self) -> dict:
        """
        Dequeue the next capture result.

        Returns:
            dict: The next capture result.
        """
        return self._queue.get()

    def empty(self) -> bool:
        """
        Check if the queue is currently empty.

        Returns:
            bool: True if queue is empty.
        """
        return self._queue.empty()
