import discord
from discord.ext.commands import Bot
from discord.ext import commands
import asyncio
import datetime
import importlib.util
from configparser import ConfigParser
import logging
from pprint import pprint

# local files
import dubucore
import modules
from lib import TwitchClient

dubucore.configureLogging()
discord_log = logging.getLogger('discord')

auth = ConfigParser()
auth.read('../dububot_secret.ini')
discord_token = auth.get('auth', 'discord_token')
twitch_token = auth.get('twitch','client_id')

custom_commands = ConfigParser()
custom_commands.read('custom_commands.ini')

config = ConfigParser()
try:
    config.read('config.ini')
except FileNotFoundError:
    discord_log.error("'config.ini' not found! Some functions will be disabled.")

# TODO: need a more modular setup that can be reloaded while running
#dubuModules = modules.Modules(auth, config)
#dubuModules.load()

Client = discord.Client()
client = commands.Bot(command_prefix = "!")

chat_filter = ["PINEAPPLE", "APPLE", "CHROME"]
bypass_list = []

@client.event
async def on_ready():
    discord_log.info("Bot is online and connected to Discord!")

@client.event
async def on_message(message):
    userID = message.author.id
    
    greeting_list = ["HELLO", "HI"]
    contents = message.content.split(" ")
    for word in contents:
        if word.upper() in greeting_list:
            await client.send_message(message.channel, "<@%s> 안녕 :heartbeat:" % (userID))

    if message.content.upper().startswith('!PING'):
        await client.send_message(message.channel, "<@%s> pong!" % (userID))

    if message.content.upper().startswith('!SAY'):
        args = message.content.split(" ")
        await client.send_message(message.channel, "%s" % (" ".join(args[1:])))

    if message.content.upper().startswith('!AMIADMIN'):
        userID = message.author.id
        if "436296739104751618" in [role.id for role in message.author.roles]:
            await client.send_message(message.channel, "<@%s> You are in the Administrators group" % (userID))
        else:
            await client.send_message(message.channel, "<@%s> You are not in the Administrators group" % (userID))

    contents = message.content.split(" ")
    for word in contents:
        if word.upper() in chat_filter:
            if not message.author.id in bypass_list:
                try:
                    await client.delete_message(message)
                    await client.send_message(message.channel, "**Hey!** You're not allowed to use that word here!")
                except discord.errors.NotFound:
                    return                

async def twitch_loop():
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
            discord_log.info("Twitch stream started: {}({})"\
                .format(s['user']['display_name'], s['id']))
            await client.send_message(channel, content=message, embed=embed)

        for s in live['stopped'].values():
            message = "{} has ended their stream ({})."\
                .format(s['user']['display_name'], s['id'])
            discord_log.info("Twitch stream stopped: {}({})"\
                .format(s['user']['display_name'], s['id']))
            await client.send_message(channel, content=message)

        await asyncio.sleep(45)

def twitch_start_message(stream):
    return "{0} is live playing {1}! https://www.twitch.tv/{0}".format(
        stream['user']['display_name'], 
        stream['game']['name'])

def twitch_start_embed(stream):
    user = stream['user']
    game = stream['game']

    embed = discord.Embed(
        description = "https://www.twitch.tv/{}".format(user['display_name']),
        timestamp = datetime.datetime.strptime(stream['started_at'],"%Y-%m-%dT%H:%M:%SZ")
    )
    embed.set_author(
            name = "{} is now live!".format(user['display_name']),
            url = "https://www.twitch.tv/{}".format(user['display_name']),
            icon_url = "https://cdn.discordapp.com/emojis/287637883022737418.png") \
         .set_thumbnail(url=user['profile_image_url'])                             \
         .set_footer(
            text="All Hail Dubu! | Broadcast started",
            icon_url="https://cdn.discordapp.com/attachments/440690304853737484/443852212326891530/unknown.png") \
         .add_field(name="Now Playing", value=game['name'])                        \
         .add_field(name="Total Views", value=user['view_count'])                  \
         .add_field(name="Stream Title", value=stream['title'])                    \
         .set_image(url=stream['thumbnail_url'].format(width=1024, height=576))
    return embed

client.loop.create_task(twitch_loop())
client.run(discord_token)
