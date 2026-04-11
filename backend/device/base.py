from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from ble.protocol import ButtonEvent

ButtonCallback     = Callable[[ButtonEvent], Awaitable[None]]
LifecycleCallback  = Callable[[], Awaitable[None]]


class AbstractDevice(ABC):
    @abstractmethod
    def register_button_callback(self, cb: ButtonCallback) -> None: ...

    @abstractmethod
    def register_connect_callback(self, cb: LifecycleCallback) -> None: ...

    @abstractmethod
    def register_disconnect_callback(self, cb: LifecycleCallback) -> None: ...

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def send_haptic_cell(self, dot_mask: int, duration_ms: int) -> None: ...

    @abstractmethod
    async def send_haptic_sequence(self, cells: list[tuple[int, int]]) -> None:
        """Send an ordered sequence of (dot_mask, duration_ms) pairs."""

    @property
    @abstractmethod
    def is_connected(self) -> bool: ...
