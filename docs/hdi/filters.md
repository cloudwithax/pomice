# Use the Filter class

Pomice takes full advantage of the Lavalink filter system by using a unique system to apply filters on top of one another. We call this system "filter stacking". With this system, we can stack any filter on top of one another to produce one-of-a-kind audio effects on playback while still being able to easily manage each filters.


## Types of filters

Lavalink, and by extension, Pomice, has different types of filters you can use.

Here are the different types and what they do:

:::{list-table}
:header-rows: 1

* - Type
  - Class
  - Description


* - Channel Mix
  - `pomice.ChannelMix()`
  - Adjusts stereo panning of a track.

* - Distortion
  - `pomice.Distortion()`
  - Generates a distortion effect on a track.
  
* - Equalizer
  - `pomice.Equalizer()`
  - Represents a 15 band equalizer. You can adjust the dynamic of the sound using this filter.

* - Karaoke
  - `pomice.Karaoke()`
  - Filters the vocals from the track.

* - Low Pass
  - `pomice.LowPass()`
  - Filters out high frequencies and only lets low frequencies pass through.

* - Rotation
  - `pomice.Rotation()`
-  Produces a stereo-like panning effect, which sounds like the audio is being rotated around the listener’s head

* - Timescale
  - `pomice.Timescale()`
  - Adjusts the speed and pitch of a track.

* - Tremolo
  - `pomice.Tremolo()`
  - Rapidly changes the volume of the track, producing a wavering tone.

* - Vibrato
  - `pomice.Vibrato()`
  - Rapidly changes the pitch of the track.


Each filter has individual values you can adjust to fine-tune the sound of the filter. If you want to see what values each filter has, refer to [](../api/filters.md).

If you are stuck on what values adjust what, some filters include presets that you can apply to get a certain sound, i.e: `pomice.Timescale` has the `vaporwave()` and `nightcore()` and so on. You can also play around with the values and generate your own unique sound if you'd like.

## Adding a filter

:::{important}

You must have the `Player` class initialized first before using this. Refer to [](player.md)

:::

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

## Removing a filter

:::{important}

You must have the `Player` class initialized first before using this. Refer to [](player.md)

:::


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


## Resetting all filters

:::{important}

You must have the `Player` class initialized first before using this. Refer to [](player.md)

:::

To reset all filters, we need to use `Player.reset_filters()`

```py

await Player.reset_filters()

```


After you have initialized your function, you can optionally include the `fast_apply` parameter, which is a boolean. If this is set to `True`, it'll remove all filters (almost) instantly if theres a track playing.

```py

await Player.reset_filters(fast_apply=<True/False>)

```

