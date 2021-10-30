"""Pomice wrapper for Lavalink, made possible by cloudwithax 2021"""
import discord

if discord.__version__ != "2.0.0a":
    class DiscordPyOutdated(Exception):
        pass

    raise DiscordPyOutdated(
        "You must have discord.py 2.0 to use this library. "
        "Uninstall your current version and install discord.py 2.0 "
        "using 'pip install git+https://github.com/Rapptz/discord.py@master'"
    )

__version__ = "1.1.1"
__title__ = "pomice"
__author__ = "cloudwithax"

from .enums import SearchType
from .events import *
from .exceptions import *
from .filters import *
from .objects import *
from .player import Player
from .pool import *
