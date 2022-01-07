"""
This example aims to show the full capabilities of the library.
This is in the form of a drop-in cog you can use and modify to your liking.
This example aims to include everything you would need to make a fully functioning music bot,
from a queue system, advanced queue control and more.
"""

import discord
import pomice
import asyncio
import math
import random

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

        # Start the node
        bot.loop.create_task(self.start_nodes())
    
    async def start_nodes(self):
        # You can pass in Spotify credentials to enable Spotify querying.
        # If you do not pass in valid Spotify credentials, Spotify querying will not work
        # Waiting for the bot to get ready before connecting to nodes.
        await self.bot.wait_until_ready() 
        await self.pomice.create_node(
            bot=self.bot,
            host="127.0.0.1",
            port="3030",
            password="youshallnotpass",
            identifier="MAIN"
        )
        print(f"Node is ready!")

    async def required(self, ctx: commands.Context):
        """Method which returns required votes based on amount of members in a channel."""
        player: Player = ctx.voice_client
        channel = self.bot.get_channel(int(player.channel.id))
        required = math.ceil((len(channel.members) - 1) / 2.5)

        if ctx.command.name == 'stop':
            if len(channel.members) == 3:
                required = 2

        return required

    async def is_privileged(self, ctx: commands.Context):
        """Check whether the user is an Admin or DJ."""
        player: Player = ctx.voice_client

        return player.dj == ctx.author or ctx.author.guild_permissions.kick_members


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
        
    @commands.command(aliases=['join', 'joi', 'j', 'summon', 'su', 'con'])
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

    @commands.command(aliases=['disconnect', 'dc', 'disc', 'lv', 'fuckoff'])
    async def leave(self, ctx: commands.Context):
        if not (player := ctx.voice_client):
            return await ctx.send("You must have the bot in a channel in order to use this command", delete_after=7)

        await player.destroy()
        await ctx.send("Player has left the channel.")
        
    @commands.command(aliases=['pla', 'p'])
    async def play(self, ctx: commands.Context, *, search: str) -> None:
        # Checks if the player is in the channel before we play anything
        if not (player := ctx.voice_client):
            await ctx.invoke(self.join)   

        # If you search a keyword, Pomice will automagically search the result using YouTube
        # You can pass in "search_type=" as an argument to change the search type
        # i.e: player.get_tracks("query", search_type=SearchType.ytmsearch)
        # will search up any keyword results on YouTube Music

        # We will also set the context here to get special features, like a track.requester object
        results = await player.get_tracks(search, ctx=ctx)     
        
        if not results:
            return await ctx.send("No results were found for that search term", delete_after=7)
        
        if isinstance(results, pomice.Playlist):
            for track in results.tracks:
                await player.queue.put(track)
        else:
            track = results[0]
            await player.queue.put(track)

        if not player.is_playing:
            await player.do_next()



    @commands.command(aliases=['pau', 'pa'])
    async def pause(self, ctx: commands.Context):
        """Pause the currently playing song."""
        if not (player := ctx.voice_client):
            return await ctx.send("You must have the bot in a channel in order to use this command", delete_after=7)

        if player.is_paused or not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send('An admin or DJ has paused the player.', delete_after=10)
            player.pause_votes.clear()

            return await player.set_pause(True)

        required = self.required(ctx)
        player.pause_votes.add(ctx.author)

        if len(player.pause_votes) >= required:
            await ctx.send('Vote to pause passed. Pausing player.', delete_after=10)
            player.pause_votes.clear()
            await player.set_pause(True)
        else:
            await ctx.send(f'{ctx.author.mention} has voted to pause the player. Votes: {len(player.pause_votes)}/{required}', delete_after=15)

    @commands.command(aliases=['res', 'r'])
    async def resume(self, ctx: commands.Context):
        """Resume a currently paused player."""
        if not (player := ctx.voice_client):
            return await ctx.send("You must have the bot in a channel in order to use this command", delete_after=7)

        if not player.is_paused or not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send('An admin or DJ has resumed the player.', delete_after=10)
            player.resume_votes.clear()

            return await player.set_pause(False)

        required = self.required(ctx)
        player.resume_votes.add(ctx.author)

        if len(player.resume_votes) >= required:
            await ctx.send('Vote to resume passed. Resuming player.', delete_after=10)
            player.resume_votes.clear()
            await player.set_pause(False)
        else:
            await ctx.send(f'{ctx.author.mention} has voted to resume the player. Votes: {len(player.resume_votes)}/{required}', delete_after=15)

    @commands.command(aliases=['n', 'nex', 'next', 'sk'])
    async def skip(self, ctx: commands.Context):
        """Skip the currently playing song."""
        if not (player := ctx.voice_client):
            return await ctx.send("You must have the bot in a channel in order to use this command", delete_after=7)

        if not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send('An admin or DJ has skipped the song.', delete_after=10)
            player.skip_votes.clear()

            return await player.stop()

        if ctx.author == player.current.requester:
            await ctx.send('The song requester has skipped the song.', delete_after=10)
            player.skip_votes.clear()

            return await player.stop()

        required = self.required(ctx)
        player.skip_votes.add(ctx.author)

        if len(player.skip_votes) >= required:
            await ctx.send('Vote to skip passed. Skipping song.', delete_after=10)
            player.skip_votes.clear()
            await player.stop()
        else:
            await ctx.send(f'{ctx.author.mention} has voted to skip the song. Votes: {len(player.skip_votes)}/{required} ', delete_after=15)

    @commands.command()
    async def stop(self, ctx: commands.Context):
        """Stop the player and clear all internal states."""
        if not (player := ctx.voice_client):
            return await ctx.send("You must have the bot in a channel in order to use this command", delete_after=7)

        if not player.is_connected:
            return

        if self.is_privileged(ctx):
            await ctx.send('An admin or DJ has stopped the player.', delete_after=10)
            return await player.teardown()

        required = self.required(ctx)
        player.stop_votes.add(ctx.author)

        if len(player.stop_votes) >= required:
            await ctx.send('Vote to stop passed. Stopping the player.', delete_after=10)
            await player.teardown()
        else:
            await ctx.send(f'{ctx.author.mention} has voted to stop the player. Votes: {len(player.stop_votes)}/{required}', delete_after=15)

    @commands.command(aliases=['mix', 'shuf'])
    async def shuffle(self, ctx: commands.Context):
        """Shuffle the players queue."""
        if not (player := ctx.voice_client):
            return await ctx.send("You must have the bot in a channel in order to use this command", delete_after=7)

        if not player.is_connected:
            return

        if player.queue.qsize() < 3:
            return await ctx.send('The queue is empty. Add some songs to shuffle the queue.', delete_after=15)

        if self.is_privileged(ctx):
            await ctx.send('An admin or DJ has shuffled the queue.', delete_after=10)
            player.shuffle_votes.clear()
            return random.shuffle(player.queue._queue)

        required = self.required(ctx)
        player.shuffle_votes.add(ctx.author)

        if len(player.shuffle_votes) >= required:
            await ctx.send('Vote to shuffle passed. Shuffling the queue.', delete_after=10)
            player.shuffle_votes.clear()
            random.shuffle(player.queue._queue)
        else:
            await ctx.send(f'{ctx.author.mention} has voted to shuffle the queue. Votes: {len(player.shuffle_votes)}/{required}', delete_after=15)

    @commands.command(aliases=['v', 'vol'])
    async def volume(self, ctx: commands.Context, *, vol: int):
        """Change the players volume, between 1 and 100."""
        if not (player := ctx.voice_client):
            return await ctx.send("You must have the bot in a channel in order to use this command", delete_after=7)

        if not player.is_connected:
            return

        if not self.is_privileged(ctx):
            return await ctx.send('Only the DJ or admins may change the volume.')

        if not 0 < vol < 101:
            return await ctx.send('Please enter a value between 1 and 100.')

        await player.set_volume(vol)
        await ctx.send(f'Set the volume to **{vol}**%', delete_after=7)

    


def setup(bot: commands.Bot):
    bot.add_cog(Music(bot))


