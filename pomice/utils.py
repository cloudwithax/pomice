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
from typing import Union, List

from discord import AutoShardedClient, Client
from discord.ext.commands import AutoShardedBot, Bot
from pomice.exceptions import OptionNotToggled

from pomice.pool import NodePool

__all__ = [
    'ExponentialBackoff',
    'NodeStats',
    'ClientType',
    'NodeAlgorithims',
    'if_toggled'
]

ClientType = Union[AutoShardedBot, AutoShardedClient, Bot, Client]

def if_toggled(option):

    def wrapper(func):

        def inner(*args, **kwargs):
            _option = NodePool._config.get(option, None)
            if not _option:
                raise OptionNotToggled(f"The `{option}` was not Toggled for the Feature `{func.__name__}`.")
            
            return func(*args, **kwargs)

        return inner

    return wrapper

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
    """The base class for the node stats object. Gives critcical information on the node, which is updated every minute."""

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
        return f'<Pomice.NodeStats total_players={self.players_total!r} playing_active={self.players_active!r}>'

class NodeAlgorithims:
    """Class that Contains Algorithims for searching Nodes or get extact Players regardless of their Node"""

    def __init__(self, data : dict) -> None:
        self.nodes = data.get("nodes", [])
        self.first = self.nodes[0] if self.nodes else None

    @classmethod
    def base(cls, nodes):
        return cls({'nodes' : random.choice(nodes)})

    @classmethod
    def best_nodes(cls, nodes, ping_wise=False, least_player=False):
        """Returns Best Node Based on the Number of Players it has"""
        if not ping_wise:
            
            return cls(
                    {'nodes' : sorted(nodes, key=lambda node: node.player_count) 
                    if least_player else nodes
                })
        else:
            if not (nodes:= [
                    node for node in nodes 
                    if (node.latency < 50 or 100 >= node.latency <= 20)
                ]):
                return None
            
            return cls(
                    {'nodes' : sorted(nodes, key=lambda node: node.player_count) 
                    if least_player else nodes
                })
    
    
    @classmethod
    def closest_nodes(cls, nodes, region,least_players = False):
        """Returns Closest Node, mainly by checking the if the Regions are Equal
        Best to Pass the Exact Region you want.
        """
        if not (nodes:=[
                n for n in nodes 
                if n.region.lower() == region.lower()
            ]):
            return None
        
        return cls(
                {'nodes': sorted(nodes, key=lambda node: node.player_count)[0] 
                if least_players else nodes[0]
            })

