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

import random
import time


__all__ = [
    'ExponentialBackoff',
    'PomiceStats'
]


class ExponentialBackoff:

    def __init__(self, base: int = 1, *, integral: bool = False) -> None:

        self._base = base

        self._exp = 0
        self._max = 10
        self._reset_time = base * 2 ** 11
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
        return self._randfunc(0, self._base * 2 ** self._exp)

class NodeStats:

    def __init__(self, data: dict) -> None:

        memory = data.get('memory')
        self.used = memory.get('used')
        self.free = memory.get('free')
        self.reservable = memory.get('reservable')
        self.allocated = memory.get('allocated')

        cpu = data.get('cpu')
        self.cpu_cores = cpu.get('cores')
        self.cpu_system_load = cpu.get('systemLoad')
        self.cpu_process_load = cpu.get('lavalinkLoad')

        self.players_active = data.get('playingPlayers')
        self.players_total = data.get('players')
        self.uptime = data.get('uptime')

    def __repr__(self) -> str:
        return f'<Pomice.NodeStats total_players={self.players_total} playing_active={self.players_active}>'


