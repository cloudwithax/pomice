# Pomice Advanced Features Guide

## 🎉 Overview

Pomice now comes with built-in advanced features to help you build powerful music bots. These features are **integrated directly into the Player and Queue classes**, providing a "batteries-included" experience.

### Key Enhancements

- **Integrated Queue & History**: Every `Player` now has its own `queue` and `history` automatically.
- **Auto-History**: Tracks are automatically added to history when they finish playing.
- **Advanced Analytics**: Detailed statistics available directly via `player.get_stats()` or `queue.get_stats()`.
- **Integrated Utilities**: Filtering, sorting, and playlist management.

---

## 📚 Table of Contents

1. [Integrated Features](#-integrated-features)
2. [Track History](#-track-history)
3. [Queue Statistics](#-queue-statistics)
4. [Playlist Manager](#-playlist-manager)
5. [Track Utilities](#-track-utilities)
6. [Complete Examples](#-complete-examples)

---

## 🚀 Integrated Features

Since these features are now part of the core classes, usage is extremely simple:

```python
# Every player now has a queue and history by default
player = ctx.voice_client

# Access the queue
player.queue.put(track)

# Play the next track from the queue
await player.do_next()

# Access the history (automatically updated)
last_song = player.history.current

# Get real-time statistics
stats = player.get_stats()
print(f"Queue Duration: {stats.format_duration(stats.total_duration)}")
```

---

## 🕐 Track History

The `player.history` object automatically tracks every song that finishes playing.

### Features
- Configurable maximum history size (default: 100)
- Navigation: `get_previous()`, `get_next()`
- Search: `history.search("query")`
- Filter: `get_by_requester(user_id)`
- Unique tracks: `get_unique_tracks()`

### Usage
```python
# Show last 10 songs
recent = player.history.get_last(10)

# Search history
results = player.history.search("Imagine Dragons")

# Play previous track
prev = player.history.get_previous()
if prev:
    await player.play(prev)
```

---

## 📊 Queue Statistics

Access advanced analytics via `player.get_stats()` or `player.queue.get_stats()`.

### Features
- Total/Average duration
- Longest/Shortest tracks
- Requester analytics (who added what)
- Author distribution
- Duration breakdown (short/medium/long)

### Usage
```python
stats = player.get_stats()
summary = stats.get_summary()

print(f"Total Tracks: {summary['total_tracks']}")
print(f"Total Duration: {summary['total_duration_formatted']}")

# Who added the most songs?
top = stats.get_top_requesters(3)
for user, count in top:
    print(f"{user.display_name}: {count} tracks")
```

---

## 💾 Playlist Manager

Export and import playlists to/from JSON and M3U formats.

### Usage
```python
import pomice

# Export current queue to file
pomice.PlaylistManager.export_queue(
    player.queue,
    filepath='playlists/party.json',
    name='Party Mix'
)

# Import a playlist
data = pomice.PlaylistManager.import_playlist('playlists/rock.json')
uris = pomice.PlaylistManager.get_track_uris('playlists/rock.json')

for uri in uris:
    results = await player.get_tracks(query=uri)
    if results:
        player.queue.put(results[0])
```

---

## 🔧 Track Utilities

Advanced filtering and sorting.

### Filtering
```python
import pomice

tracks = list(player.queue)

# Get tracks under 5 minutes
short = pomice.TrackFilter.by_duration(tracks, max_duration=300000)

# Get tracks by a specific artist
artist_songs = pomice.TrackFilter.by_author(tracks, "Artist Name")
```

### Sorting
```python
# Sort queue by title
sorted_tracks = pomice.SearchHelper.sort_by_title(list(player.queue))

# Clear and refill with sorted tracks
player.queue.clear()
player.queue.extend(sorted_tracks)
```

---

## 🎯 Complete Examples

### Integrated Music Cog

```python
import pomice
from discord.ext import commands

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def play(self, ctx, *, search: str):
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect(cls=pomice.Player)

        player = ctx.voice_client
        results = await player.get_tracks(query=search, ctx=ctx)

        if not results:
            return await ctx.send("No results.")

        track = results[0]
        player.queue.put(track)
        await ctx.send(f"Added **{track.title}** to queue.")

        if not player.is_playing:
            await player.do_next()

    @commands.command()
    async def history(self, ctx):
        """Show recently played songs."""
        player = ctx.voice_client
        recent = player.history.get_last(5)

        msg = "\n".join(f"{i}. {t.title}" for i, t in enumerate(recent, 1))
        await ctx.send(f"**Recently Played:**\n{msg}")

    @commands.command()
    async def stats(self, ctx):
        """Show queue analytics."""
        stats = ctx.voice_client.get_stats()
        summary = stats.get_summary()

        await ctx.send(
            f"**Queue Stats**\n"
            f"Tracks: {summary['total_tracks']}\n"
            f"Duration: {summary['total_duration_formatted']}"
        )
```

---

## 📖 Quick Reference

| Feature | Integrated Access |
| :--- | :--- |
| **Queue** | `player.queue` |
| **History** | `player.history` |
| **Statistics** | `player.get_stats()` |
| **Next Track** | `await player.do_next()` |

---

**Happy coding! 🎵**
