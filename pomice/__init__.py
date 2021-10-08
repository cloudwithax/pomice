"""Pomice wrapper for Lavalink, made possible by cloudwithax 2021"""

__version__ = "1.0.5"
__title__ = "pomice"
__author__ = "cloudwithax"

import discord

if discord.__version__ != '2.0.0a':
    raise exit("You must have discord.py 2.0 to use this library. Uninstall your current version and install discord.py 2.0 using 'pip install git+https://github.com/Rapptz/discord.py'")

from .enums import SearchType
from .events import *
from .exceptions import *
from .filters import *
from .pool import *
from .objects import *
from .player import Player


