"""
Pomice
~~~~~~
The modern Lavalink wrapper designed for discord.py.

:copyright: 2021, cloudwithax
:license: GPL-3.0
"""
import discord

if not discord.__version__.startswith("2.0"):
    class DiscordPyOutdated(Exception):
        pass

    raise DiscordPyOutdated(
        "You must have discord.py 2.0 to use this library. "
        "Uninstall your current version and install discord.py 2.0 "
        "using 'pip install git+https://github.com/Rapptz/discord.py@master'"
    )

__version__ = "1.1.7b"
__title__ = "pomice"
__author__ = "cloudwithax"

from .enums import SearchType
from .events import *
from .exceptions import *
from .filters import *
from .objects import *
from .player import Player
from .pool import *
from .queue import *
