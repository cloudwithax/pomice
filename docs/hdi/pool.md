# Use the NodePool class

The `NodePool` class is the first class you will use when using Pomice.

The `NodePool` Class has three main functions you can use:

- `NodePool.create_node()`
- `NodePool.get_node()`
- `NodePool.get_best_node()`


## Adding a node

To add a node to our `NodePool`, we need to run `NodePool.create_node()`.

```py

await NodePool.create_node(...)

```

After you have initialized your function, we need to fill in the proper parameters:


:::{list-table}
:header-rows: 1

* - Name
  - Type
  - Description

* - `bot`
  - `Client`
  - A discord.py `Client` object (can be either a `Client` or a `commands.Bot`)

* - `host`
  - `str`
  - The IP/URL of your Lavalink node. Remember not to include the port in this field

* - `port`
  - `int`
  - The port your Lavalink node uses. By default, Lavalink uses `2333`.

* - `identifier`
  - `str`
  - The identifier your `Node` object uses to distinguish itself.

* - `password`
  - `str`
  - The password used to connect to your node.

* - `spotify_client_id`
  - `Optional[str]`
  - Your Spotify client ID goes here. You need this along with the client secret if you want to use Spotify functionality within Pomice.

* - `spotify_client_secret`
  - `Optional[str]`
  - Your Spotify client secret goes here. You need this along with the client ID if you want to use Spotify functionality within Pomice.

* - `apple_music`
  - `bool`
  - Set this value to `True` if you want to use Apple Music functionality within Pomice. Apple Music will **not work** if you don't enable this.

* - `fallback`
  - `bool`
  - Set this value to `True` if you want Pomice to automatically switch all players to another available node if one disconnects.
    You must have two or more nodes to be able to do this.

:::


All the other parameters not listed here have default values that are either set within the function or set later in the initialization of the node. If you would like to set these parameters to a different value, you are free to do so.

After you set those parameters, your function should look something like this:

```py

await NodePool.create_node(
    bot=bot,
    host="<your ip here>",
    port=<your port here>,
    identifier="<your id here>",
    password="<your password here>",
    spotify_client_id="<your spotify client id here>",
    spotify_client_secret="<your spotify client secret here>"
    apple_music=<True/False>,
    fallback=<True/False>
)

```
:::{important}

For features like Spotify and Apple Music, you are **not required** to fill in anything for them if you do not want to use them. If you do end up queuing a Spotify or Apple Music track anyway, they will **not work** because these options are not enabled.

:::

Now that you have your Node object created, move on to [Using a node](node.md) to see what you can do with your `Node` object.

## Getting a node

To get a node from the node pool, we need to use `NodePool.get_node()`

```py

await NodePool.get_node(...)

```

After you have initialized your function, you can specify a identifier if you want to grab a specified node:

```py

await NodePool.get_node(identifier="<your id here>")

```

If you do not set a identifier, it'll return a random node from the pool.


## Getting the best node

To get a node from the node pool based on certain requirements, we need to use `NodePool.get_best_node()`

```py

await NodePool.get_best_node(...)

```

After you have initialized your function, you need to specify a `NodeAlgorithm` to use to grab your node from the pool.
The available algorithms are `by_ping` and `by_players`.
If you want to view what they do, refer to the `NodeAlgorithm` enum in the [](../api/enums.md) section.

```py

await NodePool.get_best_node(algorithm=NodeAlgorithm.xyz)

```

## Disconnecting all nodes from the pool

To disconnect all nodes from the pool, we need to use `NodePool.disconnect()`

```py

await NodePool.disconnect()

```

After running this function, all nodes in the pool should disconnect and no longer be available to use.
