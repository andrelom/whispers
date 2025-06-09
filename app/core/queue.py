import abc
import queue


class AbstractCaptureQueue(abc.ABC):
    @abc.abstractmethod
    def put(self, item: dict):
        pass

    @abc.abstractmethod
    def get(self) -> dict:
        pass

    @abc.abstractmethod
    def empty(self) -> bool:
        pass

class InMemoryCaptureQueue(AbstractCaptureQueue):
    def __init__(self):
        self._queue = queue.Queue()

    def put(self, item: dict):
        self._queue.put(item)

    def get(self) -> dict:
        return self._queue.get()

    def empty(self) -> bool:
        return self._queue.empty()
