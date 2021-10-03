import random
from typing import Optional, Type

import discord

from .exceptions import NodeCreationError, NoNodesAvailable
from .node import Node


class NodePool:
    """The base class for the node pool.
       This holds all the nodes that are to be used by the bot.
    """

    _nodes: dict = {}

    def __repr__(self):
        return f"<Pomice.NodePool node_count={self.node_count}>"

    @property
    def nodes(self):
        """Property which returns a dict with the node identifier and the Node object."""
        return self._nodes

    @property
    def node_count(self):
        return len(self._nodes.values())

    @classmethod
    def get_node(self, *, identifier: str = None) -> Node:
        """Fetches a node from the node pool using it's identifier.
           If no identifier is provided, it will choose a node at random.
        """
        available_nodes = {identifier: node for identifier, node in self._nodes.items()}
        if not available_nodes:
            raise NoNodesAvailable('There are no nodes available.')

        if identifier is None:
            return random.choice(list(available_nodes.values()))

        return available_nodes.get(identifier, None)

    @classmethod
    async def create_node(
        self,
        bot: Type[discord.Client],
        host: str,
        port: str,
        password: str,
        identifier: str,
        spotify_client_id: Optional[str] = None,
        spotify_client_secret: Optional[str] = None
    ) -> Node:
        """Creates a Node object to be then added into the node pool.
           For Spotify searching capabilites, pass in valid Spotify API credentials.
        """
        if identifier in self._nodes.keys():
            raise NodeCreationError(f"A node with identifier '{identifier}' already exists.")

        node = Node(
            pool=self, bot=bot, host=host, port=port, password=password,
            identifier=identifier, spotify_client_id=spotify_client_id,
            spotify_client_secret=spotify_client_secret
        )

        await node.connect()
        self._nodes[node._identifier] = node
        return node
