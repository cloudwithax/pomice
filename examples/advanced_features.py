"""
Example usage of Pomice's integrated advanced features.

This example shows how easy it is to use:
- Integrated Track History (auto-tracking)
- Integrated Player Queue
- Integrated Analytics with player.get_stats()
- Playlist Import/Export
"""
import discord
from discord.ext import commands

import pomice

# Initialize bot
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())


class IntegratedMusic(commands.Cog):
    """Music cog with integrated advanced features."""

    def __init__(self, bot):
        self.bot = bot
        self.pomice = pomice.NodePool()

    async def start_nodes(self):
        """Start Lavalink nodes."""
        await self.pomice.create_node(
            bot=self.bot,
            host="127.0.0.1",
            port="3030",
            password="youshallnotpass",
            identifier="MAIN",
        )

    @commands.command(name="play")
    async def play(self, ctx, *, search: str):
        """Play a track using the integrated queue."""
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect(cls=pomice.Player)

        player: pomice.Player = ctx.voice_client
        results = await player.get_tracks(query=search, ctx=ctx)

        if not results:
            return await ctx.send("No results found.")

        if isinstance(results, pomice.Playlist):
            player.queue.extend(results.tracks)
            await ctx.send(f"Added playlist **{results.name}** ({len(results.tracks)} tracks).")
        else:
            track = results[0]
            player.queue.put(track)
            await ctx.send(f"Added **{track.title}** to queue.")

        if not player.is_playing:
            await player.do_next()

    @commands.command(name="history")
    async def history(self, ctx, limit: int = 10):
        """Show recently played tracks (tracked automatically!)."""
        player: pomice.Player = ctx.voice_client
        if not player:
            return await ctx.send("Not connected.")

        if player.history.is_empty:
            return await ctx.send("No tracks in history.")

        tracks = player.history.get_last(limit)

        embed = discord.Embed(title="🎵 Recently Played", color=discord.Color.blue())
        for i, track in enumerate(tracks, 1):
            embed.add_field(name=f"{i}. {track.title}", value=f"by {track.author}", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="stats")
    async def queue_stats(self, ctx):
        """Show detailed queue statistics via integrated get_stats()."""
        player: pomice.Player = ctx.voice_client
        if not player:
            return await ctx.send("Not connected.")

        stats = player.get_stats()
        summary = stats.get_summary()

        embed = discord.Embed(title="📊 Queue Statistics", color=discord.Color.green())
        embed.add_field(name="Tracks", value=summary["total_tracks"], inline=True)
        embed.add_field(name="Duration", value=summary["total_duration_formatted"], inline=True)

        # Who added the most?
        top_requesters = stats.get_top_requesters(3)
        if top_requesters:
            text = "\n".join(f"{u.display_name}: {c} tracks" for u, c in top_requesters)
            embed.add_field(name="Top Requesters", value=text, inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="export")
    async def export_queue(self, ctx, filename: str = "my_playlist.json"):
        """Export current integrated queue."""
        player: pomice.Player = ctx.voice_client
        if not player or player.queue.is_empty:
            return await ctx.send("Queue is empty.")

        pomice.PlaylistManager.export_queue(
            player.queue,
            f"playlists/{filename}",
            name=f"{ctx.guild.name}'s Playlist",
        )
        await ctx.send(f"✅ Queue exported to `playlists/{filename}`")

    @commands.command(name="sort")
    async def sort_queue(self, ctx):
        """Sort the queue using integrated utilities."""
        player: pomice.Player = ctx.voice_client
        if not player or player.queue.is_empty:
            return await ctx.send("Queue is empty.")

        # Use SearchHelper to sort the queue list
        sorted_tracks = pomice.SearchHelper.sort_by_title(list(player.queue))

        player.queue.clear()
        player.queue.extend(sorted_tracks)
        await ctx.send("✅ Queue sorted alphabetically.")


@bot.event
async def on_ready():
    print(f"{bot.user} is ready!")


if __name__ == "__main__":
    print("Example script ready for use!")
