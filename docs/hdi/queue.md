# Use the Queue class

Pomice has an optional queue system that works seamlessly with the library. This queue system introduce quality-of-life features that every music application should ideally have like queue shuffling, queue jumping, and looping.


To use the queue system with Pomice, you must first subclass the `Player` class within your application like so:

```py

from pomice import Player

class CustomPlayer(Player):
    ...

```

After you have initialized your subclass, you can add a `queue` variable to your class so you can access your queue when you initialize your player:

```py

from pomice import Player, Queue

class CustomPlayer(Player):
    ...
    self.queue = Queue() 

```

## Adding a song to the queue

To add a song to the queue, we must use `Queue.put()`

```py

Queue.put()

```

After you have initialized your function, we need to include the `item` parameter, which is a `Track`:

```py

Queue.put(item=<your Track here>)

```

After running the function, your track should be in the queue.

## Getting a track from the queue

To get a track from the queue, we need to do a few things.

To get a track using its position within the queue, you first need to get the position as a number, also known as its index. If you dont have the index and instead want to search for its index using keywords, you have to implement a fuzzy searching algorithm to find said track using a search query as an input and have it compare that query against the titles of the tracks in the queue. After that, you can get the `Track` object by [getting it with its index](queue.md#getting-track-with-its-index)

### Getting index of track 

If you have the `Track` object and want to get its index within the queue, we can use `Queue.find_position()`

```py

Queue.find_position()

```

After you have initialized your function, we need to include the `item` parameter, which is a `Track`:

```py

Queue.find_position(item=<your Track here>)

```

After running the function, it should return the position of the track as an integer.


### Getting track with its index

If you have the index of the track and want to get the `Track` object, you first need to get the raw queue list:

```py

queue = Queue.get_queue()

```

After you have your queue, you can use basic list splicing to get the track object:

```py

track = queue[<index>]

```

## Getting the next track in the queue

To get the next track in the queue, we need to use `Queue.get()`

```py

Queue.get()

```

After running this function, it'll return the first track from the queue and remove it.

:::{note}

If you have a queue loop mode set, this behavior will be overridden since the queue is not allowed to remove tracks from the queue if its looping.

:::



