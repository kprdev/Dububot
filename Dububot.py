import discord
from discord.ext.commands import Bot
from discord.ext import commands
import asyncio
import datetime
import time
import importlib.util
from configparser import ConfigParser
import logging
from pprint import pprint
import os
import ctypes

# local files
import dubucore
import modules
from lib import TwitchClient

# Sets window name of running application if on Windows
if os.name == 'nt':
    ctypes.windll.kernel32.SetCconsoleTitleW("Dububot")

dubucore.configureLogging()
discord_log = logging.getLogger('discord')

custom_commands = ConfigParser()
custom_commands.read('custom_commands.ini')

config = ConfigParser()
try:
    config.read('config.ini')
except FileNotFoundError:
    discord_log.error("'config.ini' not found! Some functions will be disabled.")

owner = config.get('owner', 'owner_id', fallback='0')
comm_pre = config.get('chat', 'command_prefix', fallback='!')
discord_token = config.get('discord', 'token')
twitch_token = config.get('twitch','client_id', fallback=None)


# TODO: need a more modular setup that can be reloaded while running
#dubuModules = modules.Modules(auth, config)
#dubuModules.load()

Client = discord.Client()
client = commands.Bot(command_prefix = comm_pre)


@client.event
async def on_ready():
    discord_log.info("Bot is online and connected to Discord!")
    await client.change_presence(game=discord.Game(name="Dubu Dubu Dubu"))

@client.event
async def on_message(message):
    userID = message.author.id
    
    greeting_list = ["HELLO", "HI"]
    contents = message.content.split(" ")
    for word in contents:
        if word.upper() in greeting_list:
            await client.send_message(message.channel, "<@%s> 안녕 :heartbeat:" % (userID))

    if message.content.upper().startswith(comm_pre + 'PING'):
        await client.send_message(message.channel, "<@%s> pong!" % (userID))

    if message.content.upper().startswith(comm_pre + 'STATUS') and message.author.id == owner:
        game = message.content[8:]
        await client.change_presence(game=discord.Game(name=game))
        await client.send_message(message.channel, "Status has been updated to " + game)

async def twitch_loop():
    if twitch_token is None or twitch_token == '':
        discord_log.warning('Twitch token missing. No monitoring will take place.')
        return
    
    await client.wait_until_ready()
    await asyncio.sleep(2)

    twClient = TwitchClient.TwitchClient(twitch_token)
    channel = client.get_channel(config.get('twitch','AnnounceChannelId'))
    usernames = config.get('twitch','MonitorChannels').split(',')
    discord_log.info('Monitoring twitch channels: {}'.format(str(usernames)))

    while not client.is_closed:
        live = twClient.update_live_list(usernames)
        #pprint(live)

        for s in live['started'].values():
            embed = twitch_start_embed(s)
            message = twitch_start_message(s)
            discord_log.info("Twitch stream started: {} ({})"\
                .format(s['user']['login'], s['id']))
            await client.send_message(channel, content=message, embed=embed)

        for s in live['stopped'].values():
            message = "{} has ended their stream ({})."\
                .format(s['user']['display_name'], s['id'])
            discord_log.info("Twitch stream stopped: {} ({})"\
                .format(s['user']['login'], s['id']))
            await client.send_message(channel, content=message)

        await asyncio.sleep(45)

def twitch_start_message(stream):
    return "{0} is live playing {1}! https://www.twitch.tv/{2}".format(
        stream['user']['display_name'], 
        stream['game']['name'],
        stream['user']['login'])

def twitch_start_embed(stream):
    user = stream['user']
    game = stream['game']

    embed = discord.Embed(
        description = "https://www.twitch.tv/{}".format(user['login']),
        timestamp = datetime.datetime.strptime(stream['started_at'],"%Y-%m-%dT%H:%M:%SZ")
    )
    embed.set_author(
            name = "{} is now live!".format(user['display_name']),
            url = "https://www.twitch.tv/{}".format(user['login']),
            icon_url = "https://cdn.discordapp.com/emojis/287637883022737418.png") \
         .set_thumbnail(url=user['profile_image_url'])                             \
         .set_footer(
            text="All Hail Dubu! | Broadcast started",
            icon_url="https://cdn.discordapp.com/attachments/440690304853737484/443852212326891530/unknown.png") \
         .add_field(name="Now Playing", value=game['name'])                        \
         .add_field(name="Total Views", value=user['view_count'])                  \
         .add_field(name="Stream Title", value=stream['title'])                    \
         .set_image(url=stream['thumbnail_url'].format(width=1024, height=576) + '?t={}'.format(time.time()))
    return embed

client.loop.create_task(twitch_loop())
client.run(discord_token)
