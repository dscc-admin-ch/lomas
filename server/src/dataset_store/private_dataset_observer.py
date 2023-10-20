from abc import ABC, abstractmethod


class PrivateDatasetObserver(ABC):
    """
    We use this abstract class to "subscribe" to object instances
    (PrivateDataset) so that they can notify instances of this
    abstract class (LRUDatasetStore or other DatasetStore implementing
    caching) when their memory usage changes."""

    @abstractmethod
    def update_memory_usage(self) -> None:
        pass
