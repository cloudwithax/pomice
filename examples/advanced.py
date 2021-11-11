"""
This example aims to show the full capabilities of the library.
This is in the form of a drop-in cog you can use and modify to your liking.
This example aims to include everything you would need to make a fully functioning music bot,
from a queue system, advanced queue control and more.
"""

import discord
import pomice
import asyncio

from discord.ext import commands
from contextlib import suppress


class Player(pomice.Player):
    """Custom pomice Player class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
 
        self.queue = asyncio.Queue()
        self.controller: discord.Message = None
        # Set context here so we can send a now playing embed
        self.context: commands.Context = None
        self.dj: discord.Member = None

        self.pause_votes = set()
        self.resume_votes = set()
        self.skip_votes = set()
        self.shuffle_votes = set()
        self.stop_votes = set()

    async def do_next(self) -> None:
        # Clear the votes for a new song
        self.pause_votes.clear()
        self.resume_votes.clear()
        self.skip_votes.clear()
        self.shuffle_votes.clear()
        self.stop_votes.clear()

        # Check if theres a controller still active and deletes it
        if self.controller:
            with suppress(discord.HTTPException):
                await self.controller.delete()
            

       # Queue up the next track, else teardown the player
        try:
            track: pomice.Track = self.queue.get_nowait()
        except asyncio.queues.QueueEmpty:  
            return await self.teardown()

        await self.play(track)

        # Call the controller (a.k.a: The "Now Playing" embed) and check if one exists

        if track.is_stream:
            embed = discord.Embed(title="Now playing", description=f":red_circle: **LIVE** [{track.title}]({track.uri}) [{track.requester.mention}]")
            self.controller = await self.context.send(embed=embed)
        else:
            embed = discord.Embed(title=f"Now playing", description=f"[{track.title}]({track.uri}) [{track.requester.mention}]")
            self.controller = await self.context.send(embed=embed)


    async def teardown(self):
        """Clear internal states, remove player controller and disconnect."""
        with suppress((discord.HTTPException), (KeyError)):
            await self.destroy()
            if self.controller:
                await self.controller.delete() 

    async def set_context(self, ctx: commands.Context):
        """Set context for the player"""
        self.context = ctx 
        self.dj = ctx.author 




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


    # The following are events from pomice.events
    # We are using these so that if the track either stops or errors,
    # we can just skip to the next track

    # Of course, you can modify this to do whatever you like
    
    @commands.Cog.listener()
    async def on_pomice_track_end(self, player: Player, track, _):
        await player.do_next()

    @commands.Cog.listener()
    async def on_pomice_track_stuck(self, player: Player, track, _):
        await player.do_next()

    @commands.Cog.listener()
    async def on_pomice_track_exception(self, player: Player, track, _):
        await player.do_next()
        
    @commands.command(aliases=["connect"])
    async def join(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None) -> None:
        if not channel:
            channel = getattr(ctx.author.voice, "channel", None)
            if not channel:
                return await ctx.send("You must be in a voice channel in order to use this command!")

        # With the release of discord.py 1.7, you can now add a compatible
        # VoiceProtocol class as an argument in VoiceChannel.connect().
        # This library takes advantage of that and is how you initialize a player.
        await ctx.author.voice.channel.connect(cls=Player)
        player: Player = ctx.voice_client
        # Set the player context so we can use it so send messages
        player.set_context(ctx=ctx)
        await ctx.send(f"Joined the voice channel `{channel.name}`")

    @commands.command(aliases=["dc", "disconnect"])
    async def leave(self, ctx: commands.Context):
        if not ctx.voice_client:
            return await ctx.send("You must be in a voice channel in order to use this command!")

        player: pomice.Player = ctx.voice_client

        await player.destroy()
        await ctx.send("Player has left the channel.")
        
    @commands.command(aliases=["p"])
    async def play(self, ctx: commands.Context, *, search: str) -> None:
        # Checks if the player is in the channel before we play anything
        if not ctx.voice_client:
            await ctx.invoke(self.join) 

        player: Player = ctx.voice_client   

        # If you search a keyword, Pomice will automagically search the result using YouTube
        # You can pass in "search_type=" as an argument to change the search type
        # i.e: player.get_tracks("query", search_type=SearchType.ytmsearch)
        # will search up any keyword results on YouTube Music

        # We will also set the context here to get special features, like a track.requester object
        results = await player.get_tracks(search, ctx=ctx)     
        
        if not results:
            raise commands.CommandError("No results were found for that search term.")
        
        if isinstance(results, pomice.Playlist):
            for track in results.tracks:
                await player.queue.put(track)
        else:
            track = results[0]
            await player.queue.put(track)

        if not player.is_playing:
            await player.play



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


def setup(bot: commands.Bot):
    bot.add_cog(Music(bot))


