from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .pool import Node

from .utils import RouteStats

class RoutePlanner:
    """
    The base route planner class for Pomice.
    Handles all requests made to the route planner API for Lavalink.
    """

    def __init__(self, node: Node) -> None:
        self.node = node
        self.session = node._session

    async def get_status(self):
        """Gets the status of the route planner API."""
        data: dict = await self.node.send(method="GET", path="routeplanner/status")
        return RouteStats(data)


    async def free_address(self, ip: str):
        """Frees an address using the route planner API"""
        await self.node.send(method="POST", path="routeplanner/free/address", data={"address": ip})

    async def free_all_addresses(self):
        """Frees all available addresses using the route planner api"""
        await self.node.send(method="POST", path="routeplanner/free/address/all")
