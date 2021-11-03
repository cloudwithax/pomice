.. pomice documentation master file, created by
   sphinx-quickstart on Tue Nov  2 19:31:07 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Pomice!
==================

.. image:: https://raw.githubusercontent.com/cloudwithax/pomice/main/banner.jpg

The modern `Lavalink <https://github.com/freyacodes/Lavalink>`_ wrapper designed for `discord.py <https://github.com/Rapptz/discord.py>`_


Contents 
---------

.. toctree::
   modules


Before You Start
----------------

This library is designed to work with the Lavalink audio delivery system,
which directly interfaces with Discord to provide buttery smooth audio without
wasting your precious system resources. 

Pomice is made with convenience to the user, in that everything is easy to use
and is out of your way, while also being customizable.

In order to start using this library, please download a Lavalink node to start, 
you can get it `here <https://github.com/freyacodes/Lavalink/releases/latest>`_

Quick Jumpstart
----------------

If you want a quick example as to how to start with Pomice, look below:

.. code-block:: python3
   
   import pomice
   import discord
   import re

   from discord.ext import commands

   URL_REG = re.compile(r'https?://(?:www\.)?.+')

   class MyBot(commands.Bot):
      
      def __init__(self) -> None:
         super().__init__(command_prefix='!', activity=discord.Activity(type=discord.ActivityType.listening, name='to music!'))
         
         self.add_cog(Music(self))
         
      async def on_ready(self) -> None:
         print("I'm online!")
         await self.cogs["Music"].start_nodes()
      
         
   class Music(commands.Cog):
      
      def __init__(self, bot) -> None:
         self.bot = bot
         
         self.pomice = pomice.NodePool()
      
      async def start_nodes(self):
         await self.pomice.create_node(bot=self.bot, host='127.0.0.1', port='3030', 
                                       password='youshallnotpass', identifier='MAIN')
         print(f"Node is ready!")


         
      @commands.command(name='join', aliases=['connect'])
      async def join(self, ctx: commands.Context, *, channel: discord.TextChannel = None) -> None:
         
         if not channel:
               channel = getattr(ctx.author.voice, 'channel', None)
               if not channel:
                  raise commands.CheckFailure('You must be in a voice channel to use this command'
                                             'without specifying the channel argument.')

         
         await ctx.author.voice.channel.connect(cls=pomice.Player)
         await ctx.send(f'Joined the voice channel `{channel}`')
         
      @commands.command(name='play')
      async def play(self, ctx, *, search: str) -> None:
         
         if not ctx.voice_client:
               await ctx.invoke(self.join) 

         player = ctx.voice_client        

         results = await player.get_tracks(query=f'{search}')
         
         if not results:
               raise commands.CommandError('No results were found for that search term.')
         
         if isinstance(results, pomice.Playlist):
               await player.play(track=results.tracks[0])
         else:
               await player.play(track=results[0])

               
   bot = MyBot()
   bot.run("token here")




