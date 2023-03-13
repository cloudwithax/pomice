import random
import socket
import time
from datetime import datetime
from itertools import zip_longest
from timeit import default_timer as timer
from typing import Any
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import NamedTuple
from typing import Optional

from .enums import RouteIPType
from .enums import RouteStrategy

__all__ = (
    "ExponentialBackoff",
    "NodeStats",
    "FailingIPBlock",
    "RouteStats",
    "Ping",
    "LavalinkVersion",
)


class ExponentialBackoff:
    """
    The MIT License (MIT)
    Copyright (c) 2015-present Rapptz
    Permission is hereby granted, free of charge, to any person obtaining a
    copy of this software and associated documentation files (the "Software"),
    to deal in the Software without restriction, including without limitation
    the rights to use, copy, modify, merge, publish, distribute, sublicense,
    and/or sell copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following conditions:
    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.
    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
    OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.
    """

    def __init__(self, base: int = 1, *, integral: bool = False) -> None:
        self._base = base

        self._exp = 0
        self._max = 10
        self._reset_time = base * 2**11
        self._last_invocation = time.monotonic()

        rand = random.Random()
        rand.seed()

        self._randfunc = rand.randrange if integral else rand.uniform

    def delay(self) -> float:
        invocation = time.monotonic()
        interval = invocation - self._last_invocation
        self._last_invocation = invocation

        if interval > self._reset_time:
            self._exp = 0

        self._exp = min(self._exp + 1, self._max)
        return self._randfunc(0, self._base * 2**self._exp)  # type: ignore


class NodeStats:
    """The base class for the node stats object.
    Gives critical information on the node, which is updated every minute.
    """

    __slots__ = (
        "used",
        "free",
        "reservable",
        "allocated",
        "cpu_cores",
        "cpu_system_load",
        "cpu_process_load",
        "players_active",
        "players_total",
        "uptime",
    )

    def __init__(self, data: Dict[str, Any]) -> None:
        memory: dict = data.get("memory", {})
        self.used = memory.get("used")
        self.free = memory.get("free")
        self.reservable = memory.get("reservable")
        self.allocated = memory.get("allocated")

        cpu: dict = data.get("cpu", {})
        self.cpu_cores = cpu.get("cores")
        self.cpu_system_load = cpu.get("systemLoad")
        self.cpu_process_load = cpu.get("lavalinkLoad")

        self.players_active = data.get("playingPlayers")
        self.players_total = data.get("players")
        self.uptime = data.get("uptime")

    def __repr__(self) -> str:
        return f"<Pomice.NodeStats total_players={self.players_total!r} playing_active={self.players_active!r}>"


class FailingIPBlock:
    """
    The base class for the failing IP block object from the route planner stats.
    Gives critical information about any failing addresses on the block
    and the time they failed.
    """

    __slots__ = ("address", "failing_time")

    def __init__(self, data: dict) -> None:
        self.address = data.get("address")
        self.failing_time = datetime.fromtimestamp(
            float(data.get("failingTimestamp", 0)),
        )

    def __repr__(self) -> str:
        return f"<Pomice.FailingIPBlock address={self.address} failing_time={self.failing_time}>"


class RouteStats:
    """
    The base class for the route planner stats object.
    Gives critical information about the route planner strategy on the node.
    """

    __slots__ = (
        "strategy",
        "ip_block_type",
        "ip_block_size",
        "failing_addresses",
        "block_index",
        "address_index",
    )

    def __init__(self, data: Dict[str, Any]) -> None:
        self.strategy = RouteStrategy(data.get("class"))

        details: dict = data.get("details", {})

        ip_block: dict = details.get("ipBlock", {})
        self.ip_block_type = RouteIPType(ip_block.get("type"))
        self.ip_block_size = ip_block.get("size")
        self.failing_addresses = [
            FailingIPBlock(
                data,
            )
            for data in details.get("failingAddresses", [])
        ]

        self.block_index = details.get("blockIndex")
        self.address_index = details.get("currentAddressIndex")

    def __repr__(self) -> str:
        return f"<Pomice.RouteStats route_strategy={self.strategy!r} failing_addresses={len(self.failing_addresses)}>"


class Ping:
    # Thanks to https://github.com/zhengxiaowai/tcping for the nice ping impl
    def __init__(self, host: str, port: int, timeout: int = 5) -> None:
        self.timer = self.Timer()

        self._successed = 0
        self._failed = 0
        self._conn_time = None
        self._host = host
        self._port = port
        self._timeout = timeout

    class Socket:
        def __init__(self, family: int, type_: int, timeout: Optional[float]) -> None:
            s = socket.socket(family, type_)
            s.settimeout(timeout)
            self._s = s

        def connect(self, host: str, port: int) -> None:
            self._s.connect((host, port))

        def shutdown(self) -> None:
            self._s.shutdown(socket.SHUT_RD)

        def close(self) -> None:
            self._s.close()

    class Timer:
        def __init__(self) -> None:
            self._start: float = 0.0
            self._stop: float = 0.0

        def start(self) -> None:
            self._start = timer()

        def stop(self) -> None:
            self._stop = timer()

        def cost(self, funcs: Iterable[Callable], args: Any) -> float:
            self.start()
            for func, arg in zip_longest(funcs, args):
                if arg:
                    func(*arg)
                else:
                    func()

            self.stop()
            return self._stop - self._start

    def _create_socket(self, family: int, type_: int) -> Socket:
        return self.Socket(family, type_, self._timeout)

    def get_ping(self) -> float:
        s = self._create_socket(socket.AF_INET, socket.SOCK_STREAM)

        cost_time = self.timer.cost(
            (s.connect, s.shutdown),
            ((self._host, self._port), None),
        )
        s_runtime = 1000 * (cost_time)

        return s_runtime


class LavalinkVersion(NamedTuple):
    major: int
    minor: int
    fix: int

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LavalinkVersion):
            return False

        return (
            (self.major == other.major) and (self.minor == other.minor) and (self.fix == other.fix)
        )

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, LavalinkVersion):
            return False

        return not (self == other)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, LavalinkVersion):
            return False

        if self.major > other.major:
            return False
        if self.minor > other.minor:
            return False
        if self.fix > other.fix:
            return False
        return True

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, LavalinkVersion):
            return False

        return not (self < other)

    def __le__(self, other: object) -> bool:
        if not isinstance(other, LavalinkVersion):
            return False

        return (self < other) or (self == other)

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, LavalinkVersion):
            return False

        return (self > other) or (self == other)
