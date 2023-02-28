# Use the Player class

The `Player` class is the class you will be interacting with the most within Pomice.

The `Player` class has a couple functions you will be using frequently:

- `Player.add_filter()`
- `Player.destroy()`
- `Player.get_recommendations()`
- `Player.get_tracks()`
- `Player.play()`
- `Player.remove_filter()`
- `Player.reset_filters()`
- `Player.seek()`
- `Player.set_pause()`
- `Player.set_volume()`
- `Player.stop()`


There are also properties the `Player` class has to access certain values:


:::{list-table}
:header-rows: 1

* - Property
  - Type
  - Description

* - `Player.bot`
  - `Union[Client, commands.Bot]`
  - Returns the bot associated with this player instance.

* - `Player.current`
  - `Track`
  - Returns the currently playing track.

* - `Player.filters`
  - `Filters`
  - Returns the helper class for interacting with filters.

* - `Player.guild`
  - `Guild`
  - Returns the guild associated with the player.

* - `Player.is_connected`
  - `bool`
  - Returns whether or not the player is connected.

* - `Player.is_dead`
  - `bool`
  - Returns whether the player is dead or not. A player is considered dead if it has been destroyed and removed from stored players.

* - `Player.is_paused`
  - `bool`
  - Returns whether or not the player has a track which is paused or not.

* - `Player.is_playing`
  - `bool`
  - Returns whether or not the player is actively playing a track.

* - `Player.node`
  - `Node`
  - Returns the node the player is connected to.

* - `Player.position`
  - `float`
  - Returns the player’s position in a track in milliseconds.

* - `Player.volume`
  - `int`
  - Returns the players current volume.

:::

## Getting tracks

To get tracks using Lavalink, we need to use `Player.get_tracks()`

You can also use `Node.get_tracks()` to do the same thing but without having a player.

```py

await Player.get_tracks(...)

```

After you have initialized your function, we need to fill in the proper parameters:

:::{list-table}
:header-rows: 1

* - Name
  - Type
  - Description

* - `query`
  - `str`
  - The string you want to search up

* - `ctx`
  - `Optional[commands.Context]`
  - Optional value which sets a `Context` object on the tracks you search.

* - `search_type`
  - `SearchType`
  - Enum which sets the provider to search from. Default value is `SearchType.ytsearch`

* - `filters`
  - `Optional[List[Filter]]`
  - Optional value which sets the filters that should apply when the track is played on the tracks you search.

:::

After you set those parameters, your function should look something like this:

```py

await Player.get_tracks(
    query="<your query here>",
    ctx=<optional ctx object here>,
    search_type=<optional search type here>,
    filters=[<optional filters here>]
)

```

:::{important}

All querying of Spotify and Apple Music tracks or playlists is handled in this function if you enabled that functionality when creating your node.
If you want to enable it, refer to [](pool.md#adding-a-node)

:::



You should get a list of `Track` in return after running this function for you to then do whatever you want with it.
Ideally, you should be putting all tracks into some sort of a queue. If you would like to learn about how to use
our queue implementation, you can refer to [](queue.md) 


## Getting recommendations

To get recommendations using Lavalink, we need to use `Player.get_recommendations()`

You can also use `Node.get_recommendations()` to do the same thing without having a player.

```py

await Player.get_recommendations(...)

```

After you have initialized your function, we need to fill in the proper parameters:

:::{list-table}
:header-rows: 1

* - Name
  - Type
  - Description

* - `track`
  - `Track`
  - The track to fetch recommendations for

* - `ctx`
  - `Optional[commands.Context]`
  - Optional value which sets a `Context` object on the recommendations you fetch.

:::

After you set those parameters, your function should look something like this:

```py

await Player.get_recommendations(
    track=<your track object here>,
    ctx=<optional ctx object here>,
)

```

You should get a list of `Track` in return after running this function for you to then do whatever you want with it.
Ideally, you should be putting all tracks into some sort of a queue. If you would like to learn about how to use
our queue implementation, you can refer to [](queue.md) 

## Connecting a player

To connect a player to a channel you need to pass the `Player` class into your `channel.connect()` function:

```py

await voice_channel.connect(cls=Player)

```

This will instance the player and make it available to your guild. If you want to access your player after instancing it,
you must use either `Guild.voice_client` or `Context.voice_client`.

## Controlling the player

There are a few functions to control the player:

- `Player.destroy()`
- `Player.play()`
- `Player.seek()`
- `Player.set_pause()`
- `Player.set_volume()`
- `Player.stop()`

### Destroying a player

To destroy a player, we need to use `Player.destroy()`

```py

await Player.destroy()

```

### Playing a track

To play a track, we need to use `Player.play()`

```py

await Player.play(...)

```

After you have initialized your function, we need to fill in the proper parameters:

:::{list-table}
:header-rows: 1

* - Name
  - Type
  - Description

* - `track`
  - `Track`
  - The track to play

* - `start`
  - `int`
  - The time (in milliseconds) to start the track at. Default value is `0`

* - `end`
  - `int`
  - The time (in milliseconds) to end the track at. Default value is `0`

* - `ignore_if_playing`
  - `bool`
  - If set, ignores the current track playing and replaces it with this track. Default value is `False`



:::

After you set those parameters, your function should look something like this:

```py

await Player.play(
    track=<your track object here>,
    start=<your optional start time here>,
    end=<your optional end time here>,
    ignore_if_playing=<your optional boolean here>
)

```

After running this function, it should return the `Track` you specified when running the function. This means the track is now playing.


### Seeking to a position 

To seek to a position, we need to use `Player.seek()`

```py

await Player.seek(...)

```

After you have initialized your function, we need to include the `position` parameter, which is an amount in milliseconds:

```py

await Player.seek(position=<your pos here>)

```

After running this function, your currently playing track should seek to your specified position


### Pausing/unpausing the player


To pause/unpause the player, we need to use `Player.set_pause()`

```py

await Player.set_pause(...)

```

After you have initialized your function, we need to include the `pause` parameter, which is a boolean:

```py

await Player.set_pause(pause=<True/False>)

```
After running this function, your currently playing track should either pause or unpause depending on what you set.

### Setting the player volume

To set the volume the player, we need to use `Player.set_volume()`

```py

await Player.set_volume(...)

```

:::{important}
Lavalink accept ranges from 0 to 500 for this parameter. Inputting a value either higher or lower
than this amount will **not work.**
:::

After you have initialized your function, we need to include the `amount` parameter, which is an integer:

```py

await Player.set_volume(amount=<int>)

```
After running this function, your currently playing track should adjust in volume depending on the amount you set.

### Stopping the player

To stop the player, we need to use `Player.stop()`

```py

await Player.stop()

```

## Controlling filters

Pomice has an extensive suite of filter management tools to help you make the most of Lavalink and it's filters.

Here are some of the functions you will be using to control filters:

- `Player.add_filter()`
- `Player.remove_filter()`
- `Player.reset_filters()`


### Adding a filter


To add a filter, we need to use `Player.add_filter()`

```py

await Player.add_filter(...)

```


After you have initialized your function, we need to fill in the proper parameters:

:::{list-table}
:header-rows: 1

* - Name
  - Type
  - Description

* - `filter`
  - `Filter`
  - The filter to apply

* - `fast_apply`
  - `bool`
  - If set to `True`, the specified filter will apply (almost) instantly if a song is playing. Default value is `False`.

:::

After you set those parameters, your function should look something like this:

```py

await Player.add_filter(
    filter=<your filter object here>,
    fast_apply=<True/False>
)

```

After running this function, you should see your currently playing track sound different depending on the filter you chose.

### Removing a filter


To remove a filter, we need to use `Player.remove_filter()`

```py

await Player.remove_filter(...)

```


After you have initialized your function, we need to fill in the proper parameters:

:::{list-table}
:header-rows: 1

* - Name
  - Type
  - Description

* - `filter`
  - `Filter`
  - The filter to remove

* - `fast_apply`
  - `bool`
  - If set to `True`, the specified filter will be removed (almost) instantly if a song is playing. Default value is `False`.

:::

After you set those parameters, your function should look something like this:

```py

await Player.remove_filter(
    filter=<your filter object here>,
    fast_apply=<True/False>
)

```

After running this function, you should see your currently playing track sound different depending on the filter you chose to remove.


### Resetting all filters

To reset all filters, we need to use `Player.reset_filters()`

```py

await Player.reset_filters()

```














