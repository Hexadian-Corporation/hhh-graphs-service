from abc import ABC, abstractmethod


class ImportEventSubscriber(ABC):
    @abstractmethod
    async def start(self) -> None:
        """Start listening to import events in the background."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Signal the subscriber to stop and await its completion."""
        ...
