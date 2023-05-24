# Pomice

![](https://raw.githubusercontent.com/cloudwithax/pomice/main/banner.jpg)


[![GPL](https://img.shields.io/github/license/cloudwithax/pomice?color=2f2f2f)](https://github.com/cloudwithax/pomice/blob/main/LICENSE) ![](https://img.shields.io/pypi/pyversions/pomice?color=2f2f2f) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Discord](https://img.shields.io/discord/899324069235810315?color=%237289DA&label=Pomice%20Support&logo=discord&logoColor=white)](https://discord.gg/r64qjTSHG8) [![Read the Docs](https://readthedocs.org/projects/pomice/badge/?version=latest)](https://pomice.readthedocs.io/en/latest/)


Pomice is a fully asynchronous Python library designed for communicating with [Lavalink](https://github.com/freyacodes/Lavalink). It features 100% coverage of the [Lavalink](https://github.com/freyacodes/Lavalink) spec that can be accessed with easy-to-understand functions along with Spotify and Apple Music querying capabilities using built-in custom clients, making it easier to develop your next big music bot.

## Quick Links
- [Discord Server](https://discord.gg/r64qjTSHG8)
- [Read the Docs](https://pomice.readthedocs.io/en/latest/)
- [PyPI Homepage](https://pypi.org/project/pomice/)


# Install
To install the library, you need the lastest version of pip and minimum Python 3.8

> Stable version
```
pip install pomice
```

> Unstable version (this one gets more frequent changes)
```
pip install git+https://github.com/cloudwithax/pomice
```

# Support And Documentation

The official documentation is [here](https://pomice.readthedocs.io/en/latest/)

You can join our support server [here](https://discord.gg/r64qjTSHG8)


# Examples
In-depth examples are located in the [examples folder](https://github.com/cloudwithax/pomice/tree/main/examples)

Here's a quick example:

```py
import pomice
import discord
import re

from discord.ext import commands

URL_REG = re.compile(r'https?://(?:www\.)?.+')

class MyBot(commands.Bot):

    def __init__(self) -> None:
        super().__init__(command_prefix='!', activity=discord.Activity(type=discord.ActivityType.listening, name='to music!'))

        self.add_cog(Music(self))

    async def on_ready(self) -> None:
        print("I'm online!")
        await self.cogs["Music"].start_nodes()


class Music(commands.Cog):

    def __init__(self, bot) -> None:
        self.bot = bot

        self.pomice = pomice.NodePool()

    async def start_nodes(self):
        await self.pomice.create_node(bot=self.bot, host='127.0.0.1', port='3030',
                                     password='youshallnotpass', identifier='MAIN')
        print(f"Node is ready!")



    @commands.command(name='join', aliases=['connect'])
    async def join(self, ctx: commands.Context, *, channel: discord.TextChannel = None) -> None:

        if not channel:
            channel = getattr(ctx.author.voice, 'channel', None)
            if not channel:
                raise commands.CheckFailure('You must be in a voice channel to use this command'
                                            'without specifying the channel argument.')


        await ctx.author.voice.channel.connect(cls=pomice.Player)
        await ctx.send(f'Joined the voice channel `{channel}`')

    @commands.command(name='play')
    async def play(self, ctx, *, search: str) -> None:

        if not ctx.voice_client:
            await ctx.invoke(self.join)

        player = ctx.voice_client

        results = await player.get_tracks(query=f'{search}')

        if not results:
            raise commands.CommandError('No results were found for that search term.')

        if isinstance(results, pomice.Playlist):
            await player.play(track=results.tracks[0])
        else:
            await player.play(track=results[0])


bot = MyBot()
bot.run("token here")
 ```

# FAQ
Why is it saying "Cannot connect to host"?

- You need to have a Lavalink node setup before you can use this library. Download it [here](https://github.com/freyacodes/Lavalink/releases/latest)

What experience do I need?

- This library requires that you have some experience with Python, asynchronous programming and the discord.py library.

Why is it saying "No module named pomice found"?

- You need to [install](#Install) the package before you can use it

# Contributors

- Thanks to [vveeps](https://github.com/vveeps) for implementing some features I wasn't able to do myself
