# Quick Jumpstart


If you want a quick example as to how to start with Pomice, look below:

```py
import pomice
import discord
import re

from discord.ext import commands

URL_REG = re.compile(r"https?://(?:www\.)?.+")


class MyBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix="!",
            activity=discord.Activity(
                type=discord.ActivityType.listening, name="to music!"
            ),
        )

        self.add_cog(Music(self))

    async def on_ready(self) -> None:
        print("I'm online!")
        await self.cogs["Music"].start_nodes()


class Music(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

        self.pomice = pomice.NodePool()

    async def start_nodes(self):
        await self.pomice.create_node(
            bot=self.bot,
            host="127.0.0.1",
            port="3030",
            password="youshallnotpass",
            identifier="MAIN",
        )
        print(f"Node is ready!")

    @commands.command(name="join", aliases=["connect"])
    async def join(
        self, ctx: commands.Context, *, channel: discord.TextChannel = None
    ) -> None:
        if not channel:
            channel = getattr(ctx.author.voice, "channel", None)
            if not channel:
                raise commands.CheckFailure(
                    "You must be in a voice channel to use this command"
                    "without specifying the channel argument."
                )

        await ctx.author.voice.channel.connect(cls=pomice.Player)
        await ctx.send(f"Joined the voice channel `{channel}`")

    @commands.command(name="play")
    async def play(self, ctx, *, search: str) -> None:
        if not ctx.voice_client:
            await ctx.invoke(self.join)

        player = ctx.voice_client

        results = await player.get_tracks(query=f"{search}")

        if not results:
            raise commands.CommandError("No results were found for that search term.")

        if isinstance(results, pomice.Playlist):
            await player.play(track=results.tracks[0])
        else:
            await player.play(track=results[0])


bot = MyBot()
bot.run("token here")
```
