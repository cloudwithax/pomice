# Use the Node class

The `Node` class is one of the main classes you will be interacting with when using Pomice.

The `Node` class has a couple functions you will be using frequently:

- `Node.get_player()`
- `Node.get_tracks()`
- `Node.get_recommendations()`


There are also properties the `Node` class has to access certain values:

:::{list-table}
:header-rows: 1

* - Property
  - Type
  - Description

* - `Node.bot`
  - `Client`
  - Returns the discord.py client linked to this node.

* - `Node.is_connected`
  - `bool`
  - Returns whether this node is connected or not.

* - `Node.latency` `Node.ping`
  - `float`
  - Returns the latency of the node.

* - `Node.player_count`
  - `int`
  - Returns how many players are connected to this node.

* - `Node.players`
  - `Dict[int, Player]`
  - Returns a dict containing the guild ID and the player object.

* - `Node.pool`
  - `NodePool`
  - Returns the pool this node is apart of.

* - `Node.stats`
  - `NodeStats`
  - Returns the nodes stats.

:::

## Getting a player

To get a player from the nodes list of players, we need to use `Node.get_player()`

```py

await Node.get_player(...)

```

After you have initialized your function, you need to specify the `guild_id` of the player.

```py

await Node.get_player(guild_id=<your guild ID here>)

```

If the node finds a player with the guild ID you provided, it'll return the [](../api/player.md) object associated with the guild ID.


## Getting tracks

To get tracks using Lavalink, we need to use `Node.get_tracks()`

You can also use `Player.get_tracks()` to do the same thing, but this can be used to fetch tracks regardless if a player exists.

```py

await Node.get_tracks(...)

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

await Node.get_tracks(
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

To get recommadations using Lavalink, we need to use `Node.get_recommendations()`

You can also use `Player.get_recommendations()` to do the same thing, but this can be used to fetch recommendations regardless if a player exists.

```py

await Node.get_recommendations(...)

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

await Node.get_recommendations(
    track=<your track object here>,
    ctx=<optional ctx object here>,
)

```

You should get a list of `Track` in return after running this function for you to then do whatever you want with it.
Ideally, you should be putting all tracks into some sort of a queue. If you would like to learn about how to use
our queue implementation, you can refer to [](queue.md)
