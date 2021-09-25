import discord
import typing
import random

from . import exceptions
from .node import Node

from discord.ext import commands


class NodePool:
    
    _nodes: dict = {}

    def __repr__(self):
        return f"<Pomice.NodePool node_count={len(self._nodes.values())}>"

    @property
    def nodes(self):
        return self._nodes
    

    @classmethod
    def get_node(self, *, identifier: str = None) -> Node:
        available_nodes = {identifier: node for identifier, node in self._nodes.items()}
        if not available_nodes:
            raise exceptions.NoNodesAvailable('There are no nodes available.')

        if identifier is None:
            return random.choice(list(available_nodes.values()))

        return available_nodes.get(identifier, None)
     
    @classmethod
    async def create_node(self, bot: typing.Union[commands.Bot, discord.Client, commands.AutoShardedBot, discord.AutoShardedClient], host: str, port: str, password: str, identifier: str) -> Node:
        if identifier in self._nodes.keys():
            raise exceptions.NodeCreationError(f"A node with identifier '{identifier}' already exists.")

        node = Node(pool=self, bot=bot, host=host, port=port, password=password, identifier=identifier)
        await node.connect()
        self._nodes[node._identifier] = node
        return node



    