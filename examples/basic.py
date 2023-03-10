import discord
import pomice
from discord.ext import commands


class MyBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix="!",
            activity=discord.Activity(type=discord.ActivityType.listening, name="to music!")
        )

        self.add_cog(Music(self))
        self.loop.create_task(self.cogs["Music"].start_nodes())

    async def on_ready(self) -> None:
        print("I'm online!")


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        # In order to initialize a node, or really do anything in this library,
        # you need to make a node pool
        self.pomice = pomice.NodePool()

    async def start_nodes(self):
        # You can pass in Spotify credentials to enable Spotify querying.
        # If you do not pass in valid Spotify credentials, Spotify querying will not work
        await self.pomice.create_node(
            bot=self.bot,
            host="127.0.0.1",
            port="3030",
            password="youshallnotpass",
            identifier="MAIN"
        )
        print(f"Node is ready!")

    @commands.command(aliases=["connect"])
    async def join(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None) -> None:
        if not channel:
            channel = getattr(ctx.author.voice, "channel", None)
            if not channel:
                raise commands.CheckFailure(
                    "You must be in a voice channel to use this command "
                    "without specifying the channel argument."
                )

        # With the release of discord.py 1.7, you can now add a compatible
        # VoiceProtocol class as an argument in VoiceChannel.connect().
        # This library takes advantage of that and is how you initialize a player.
        await ctx.author.voice.channel.connect(cls=pomice.Player)
        await ctx.send(f"Joined the voice channel `{channel}`")

    @commands.command(aliases=["dc", "disconnect"])
    async def leave(self, ctx: commands.Context):
        if not ctx.voice_client:
            raise commands.CommandError("No player detected")

        player: pomice.Player = ctx.voice_client

        await player.destroy()
        await ctx.send("Player has left the channel.")

    @commands.command(aliases=["p"])
    async def play(self, ctx: commands.Context, *, search: str) -> None:
        # Checks if the player is in the channel before we play anything
        if not ctx.voice_client:
            await ctx.invoke(self.join)

        player: pomice.Player = ctx.voice_client

        # If you search a keyword, Pomice will automagically search the result using YouTube
        # You can pass in "search_type=" as an argument to change the search type
        # i.e: player.get_tracks("query", search_type=SearchType.ytmsearch)
        # will search up any keyword results on YouTube Music
        results = await player.get_tracks(search)

        if not results:
            raise commands.CommandError("No results were found for that search term.")

        if isinstance(results, pomice.Playlist):
            await player.play(track=results.tracks[0])
        else:
            await player.play(track=results[0])

    @commands.command()
    async def pause(self, ctx: commands.Context):
        if not ctx.voice_client:
            raise commands.CommandError("No player detected")

        player: pomice.Player = ctx.voice_client

        if player.is_paused:
            return await ctx.send("Player is already paused!")

        await player.set_pause(pause=True)
        await ctx.send("Player has been paused")

    @commands.command()
    async def resume(self, ctx: commands.Context):
        if not ctx.voice_client:
            raise commands.CommandError("No player detected")

        player: pomice.Player = ctx.voice_client

        if not player.is_paused:
            return await ctx.send("Player is already playing!")

        await player.set_pause(pause=False)
        await ctx.send("Player has been resumed")

    @commands.command()
    async def stop(self, ctx: commands.Context):
        if not ctx.voice_client:
            raise commands.CommandError("No player detected")

        player: pomice.Player = ctx.voice_client

        if not player.is_playing:
            return await ctx.send("Player is already stopped!")

        await player.stop()
        await ctx.send("Player has been stopped")


bot = MyBot()
bot.run("token")
