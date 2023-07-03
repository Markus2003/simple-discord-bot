##############################################
#                Basic Imports               #
##############################################
import asyncio
import json
import os
import random
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from os import rename, remove
from os.path import exists as fileExists

import discord
from requests import get
from yt_dlp import YoutubeDL

import src.res.discordEmoji as discordEmoji
import src.res.discordLogger as discordLogger
import src.res.printStatusToConsole as printStatus

##############################################
#                                            #
##############################################


##############################################
#                  Variables                 #
##############################################
BOT_NAME = None
BOT_TOKEN = None
BOT_PREFIX = None
BOT_AVATAR = None
BOT_ACCENT_COLOR = None
BOT_EMBED_FOOTER = None
BOT_GAME_PRESENCE = None
BOT_AMIN_ROLE = None
BOT_SERVICES_ALLOWED = []
BOT_SERVICES_MAINTEINANCE = []
BOT_FEATURES_ENABLED = []
BOT_FEATURES_DISABLED = []
BOT_VERSION = None

GATCHA_CURRENT_PITY = 0
GATCHA_MAX_PITY = 90
GATCHA_50_50_LOOSE = []

WORKING_DIR = os.getcwd()
BUFFER_DIR = f"{WORKING_DIR}/buffer/"
BUFFER_JSON = f"{WORKING_DIR}/buffer.json"
PREFIX_YT = "https://www.youtube.com/watch?v="

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': False,
    'ignoreerrors': True,
    'keepvideo': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}
ytdl = YoutubeDL( ytdl_format_options )

music_queue = []
songBuffer = []
is_playing = False
is_paused = False
loopStatus = "off"

guild_count = 0

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

threadStopper = threading.Event()
threadCondition = threading.Condition()

vc = None
##############################################
#                                            #
##############################################


##############################################
#          Buffer Related Functions          #
##############################################
# Retrieve the number of song present in (0) Folder or in (1) 'buffer.json'
def number_of_song_buffered ( from_where = 0 ):
    counter = 0
    if from_where == 0:
        for file in os.scandir( f"{BUFFER_DIR}" ):
            if file.is_file() and file.name.endswith( ".mp3" ):
                counter = counter + 1
    
    else:
        with open( f"{BUFFER_JSON}", "r" ) as external_DB:
            counter = len( json.load( external_DB ) )
            external_DB.close()

    return counter


# Wipe the buffer folder and the 'buffer.json'
def wipe_buffer ():
    with open( f"{BUFFER_JSON}", "w" ) as external_DB:
        json.dump([], external_DB, indent=4)
        external_DB.close()
    
    for file in os.scandir( f"{BUFFER_DIR}" ):
        if file.is_file() and file.name.endswith( ".mp3" ):
            os.unlink( f"{BUFFER_DIR}{file.name}" )


# Extract the video ID at the end of the URL
def id_from_url ( song_link ):
    return song_link.split("?")[1].replace( "v=", "" )


# DatabaseQuery-like to search an element (song) in 'buffer.json'
def SELECT ( buffer, index_title, term, return_type ):
    if index_title not in [ "webpage_id", "uuid" ]:
        return None

    internal_DB = []
    with open( buffer, "r" ) as external_DB:
        internal_DB = json.load( external_DB )
        external_DB.close()

    for index in range( 0, len( internal_DB ) ):
        if term == internal_DB[ index ][ index_title ]:
            if return_type == 0:
                return index

            else:
                return internal_DB[ index ]

    return None


# DatabaseQuery-like to insert an element (song) in 'buffer.json'
def INSERT ( buffer, args ):
    internal_DB = []
    with open( buffer, "r" ) as external_DB:
        internal_DB = json.load( external_DB )
        external_DB.close()

    if SELECT( buffer, "webpage_id", args[0], 0 ) == None :
        temp = {
            "webpage_id": args[0],
            "title": args[1],
            "uuid": args[2],
            "available": args[3]
        }
        internal_DB.append( temp )
        with open( buffer, "w" ) as external_DB:
            json.dump( internal_DB, external_DB, indent=4 )
            external_DB.close()
        
        return True

    else:
        return False


# DatabaseQuery-like to delete an element (song) in 'buffer.json'
def DELETE ( buffer, webpage_id ):
    if SELECT( buffer, "webpage_id", webpage_id, 0 ) != None:
        internal_DB = []
        with open( buffer, "r" ) as external_DB:
            internal_DB = json.load( external_DB )
            external_DB.close()

        internal_DB.pop( SELECT( buffer, "webpage_id", webpage_id, 0 ) )
        with open( buffer, "w" ) as external_DB:
            json.dump( internal_DB, external_DB, indent=4 )
            external_DB.close()

        return True

    else:
        return False

# DatabaseQuery-like to edit an element (song) in 'buffer.json'
def UPDATE ( buffer, row_title_identifier, row_term_identifier, index_title, new_term ):
    if row_title_identifier not in [ "webpage_id", "uuid" ] or index_title not in [ "webpage_id", "title", "uuid", "available" ]:
        return None

    if SELECT( buffer, row_title_identifier, row_term_identifier, 0 ) == None:
        return False

    else:
        internal_DB = []
        with open( buffer, "r" ) as external_DB:
            internal_DB = json.load( external_DB )
            external_DB.close()

        internal_DB[ SELECT( buffer, row_title_identifier, row_term_identifier, 0 ) ][ index_title ] = new_term
        with open( buffer, "w" ) as external_DB:
            json.dump( internal_DB, external_DB, indent=4 )
            external_DB.close()

        return True

    return None


# Function to be exeuted as a thread to provide a background bufferring while streaming
def fastBuffer ( uuid, link ):
    buffer_opts = {
        'format': 'bestaudio/best',
        'keepvideo': False,
        'outtmpl': f'{BUFFER_DIR}{str( uuid )}.webm',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    with YoutubeDL( buffer_opts ) as ydl:
        ydl.download([link])

    UPDATE( BUFFER_JSON, "uuid", uuid, "available", True )


# Preliminar Checks on Buffer Folder and 'buffer.json'
if not os.path.isdir( f"{BUFFER_DIR}" ):
    os.mkdir( f"{BUFFER_DIR}" )
    if os.path.isfile( f"{BUFFER_JSON}" ):
        os.unlink( f"{BUFFER_JSON}" )

if not os.path.isfile( f"{BUFFER_JSON}" ):
    with open( f"{BUFFER_JSON}", "w" ) as external_DB:
        json.dump([], external_DB)
        external_DB.close()

else:
    if number_of_song_buffered( 0 ) != number_of_song_buffered( 1 ):
        wipe_buffer()
##############################################
#                                            #
##############################################


##############################################
#           Music Player Functions           #
##############################################
# Given a Song Name search the appropriate URL on YouTube
def search(arg):
    with YoutubeDL( ytdl_format_options ) as ydl:
        try:
            get(arg)
        except:
            video = ydl.extract_info(f"ytsearch:{arg}", download=False)['entries'][0]
        else:
            video = ydl.extract_info(arg, download=False)

    return video

# Handler to play all the song in the queue
async def play_next_song ( message ):
    global is_playing, vc, music_queue, loopStatus, songBuffer
    current_song =  music_queue.pop(0)
    user_voice_channel = message.author.voice.channel
    try:
        vc = await user_voice_channel.connect()

    except:
        pass

    if checkService('caching') == 1:
        if current_song[3] != None:
            if current_song[2] == False:
                try:
                    if SELECT( BUFFER_JSON, "uuid", current_song[3], 1 )['available'] == True:
                        current_song[0] = discord.FFmpegPCMAudio( f"{BUFFER_DIR}{current_song[3]}.mp3" )

                except Exception:
                    print("Exception in queue handling")
                    pass

    vc.play(current_song[0], after=lambda e: print('Player error: %s' % e) if e else None)
    await message.channel.send( f"Playing **{discordEmoji.MUSIC_NOTE} {current_song[1]} {discordEmoji.MUSIC_NOTE}**", reference=message )
    while vc.is_playing() or is_paused:
        await asyncio.sleep(0.1)

    await vc.disconnect()
    is_playing = False

    if loopStatus == "once":
        music_queue.insert( 0, current_song )

    if loopStatus == "all":
        songBuffer.append( currentSong )

    if music_queue == [] and loopStatus == "all" and songBuffer != []:
        music_queue = songBuffer

    if music_queue:
        await play_next_song( message )

    else:
        if loopStatus != "off":
            loopStatus = "off"
            await message.channel.send(f"Loop status ha been resetted to: `{loopStatus}`")
##############################################
#                                            #
##############################################


##############################################
#         General Purpouse Functions         #
##############################################
# Import all confings from 'settings.json' (or 'resetSettings.json')
def importConfigs( additionalTab = 0, source='default' ):
    global BOT_NAME, BOT_TOKEN, BOT_PREFIX, BOT_AVATAR, BOT_ACCENT_COLOR, BOT_EMBED_FOOTER, BOT_GAME_PRESENCE, BOT_ADMIN_ROLE, BOT_SERVICES_ALLOWED, BOT_SERVICES_MAINTEINANCE, BOT_FEATURES_ENABLED, BOT_FEATURES_DISABLED, GATCHA_CURRENT_PITY, GATCHA_MAX_PITY, GATCHA_50_50_LOOSE, BOT_VERSION
    printStatus.work( "Importing Configs...", 1 + additionalTab )
    settingsFileLocation= None
    if source == 'reset':
        settingsFileLocation = "resetSettings.json"

    else:
        settingsFileLocation = "settings.json"

    try:
        with open( f'src/configs/{settingsFileLocation}', 'r' ) as settingsFile:
            settings = json.load( settingsFile )
            BOT_NAME = settings['BOT_NAME']
            printStatus.info( f"Imported: BOT_NAME -> {BOT_NAME}", 2 + additionalTab )
            BOT_TOKEN = settings['BOT_TOKEN']
            printStatus.info( f"Imported: BOT_TOKEN -> {BOT_TOKEN}", 2 + additionalTab )
            BOT_PREFIX = settings['BOT_PREFIX']
            printStatus.info( f"Imported: BOT_PREFIX -> {BOT_PREFIX}", 2 + additionalTab )
            BOT_AVATAR = settings['BOT_AVATAR']
            printStatus.info( f"Imported: BOT_AVATAR -> {BOT_AVATAR}", 2 + additionalTab )
            BOT_ACCENT_COLOR = settings['BOT_ACCENT_COLOR']
            printStatus.info( f"Imported: BOT_ACCENT_COLOR -> {BOT_ACCENT_COLOR}", 2 + additionalTab )
            BOT_EMBED_FOOTER = settings['BOT_EMBED_FOOTER']
            printStatus.info( f"Imported: BOT_EMBED_FOOTER -> {BOT_EMBED_FOOTER}", 2 + additionalTab )
            BOT_GAME_PRESENCE = settings['BOT_GAME_PRESENCE']
            printStatus.info( f"Imported: BOT_GAME_PRESENCE -> {BOT_GAME_PRESENCE}", 2 + additionalTab )
            BOT_ADMIN_ROLE = settings['BOT_ADMIN_ROLE']
            printStatus.info( f"Imported: BOT_ADMIN_ROLE -> {BOT_ADMIN_ROLE}", 2 + additionalTab )
            BOT_SERVICES_ALLOWED = settings['BOT_SERVICES_ALLOWED']
            printStatus.info( f"Imported: BOT_SERVICES_ALLOWED -> {BOT_SERVICES_ALLOWED}", 2 + additionalTab )
            BOT_SERVICES_MAINTEINANCE = settings['BOT_SERVICES_MAINTEINANCE']
            printStatus.info( f"Imported: BOT_SERVICES_MAINTEINANCE -> {BOT_SERVICES_MAINTEINANCE}", 2 + additionalTab )
            BOT_FEATURES_ENABLED = settings['BOT_FEATURES_ENABLED']
            printStatus.info( f"Imported: BOT_FEATURES_ENABLED -> {BOT_FEATURES_ENABLED}", 2 + additionalTab )
            BOT_FEATURES_DISABLED = settings['BOT_FEATURES_DISABLED']
            printStatus.info( f"Imported: BOT_FEATURES_DISABLED -> {BOT_FEATURES_DISABLED}", 2 + additionalTab )
            GATCHA_CURRENT_PITY = settings['BOT_GATCHA']['GATCHA_CURRENT_PITY']
            printStatus.info( f"Imported: GATCHA_CURRENT_PITY -> {GATCHA_CURRENT_PITY}", 2 + additionalTab )
            GATCHA_MAX_PITY = settings['BOT_GATCHA']['GATCHA_MAX_PITY']
            printStatus.info( f"Imported: GATCHA_MAX_PITY -> {GATCHA_MAX_PITY}", 2 + additionalTab )
            GATCHA_50_50_LOOSE = settings['BOT_GATCHA']['GATCHA_50_50_LOOSE']
            printStatus.info( f"Imported: GATCHA_50_50_LOOSE -> {GATCHA_50_50_LOOSE}", 2 + additionalTab )
            BOT_VERSION = settings['BOT_VERSION']
            printStatus.info( f"Imported: BOT_VERSION -> {BOT_VERSION}", 2 + additionalTab )
            settingsFile.close()

    except Exception as e:
        printStatus.fail( "Error importing Configs: " + str(e), 1 + additionalTab )
        printStatus.fail( "Bot hasn't started successfully, exiting...", 0 + additionalTab )
        exit()

    printStatus.success_green( "Configs imported successfully!", 1 + additionalTab )

# Save the current settings on 'settings.json'
def updateSettings():
    global BOT_NAME, BOT_TOKEN, BOT_PREFIX, BOT_AVATAR, BOT_ACCENT_COLOR, BOT_EMBED_FOOTER, BOT_GAME_PRESENCE, BOT_ADMIN_ROLE, BOT_SERVICES_ALLOWED, BOT_SERVICES_MAINTEINANCE, BOT_FEATURES_ENABLED, BOT_FEATURES_DISABLED, GATCHA_CURRENT_PITY, GATCHA_MAX_PITY, GATCHA_50_50_LOOSE, BOT_VERSION
    printStatus.work( "Updating Configs...", 2 )
    try:
        settings = None

        with open( 'src/configs/settings.json', 'r' ) as settingsFile:
            settings = json.load( settingsFile )
            settingsFile.close()

        settings['BOT_NAME'] = BOT_NAME
        settings['BOT_TOKEN'] = BOT_TOKEN
        settings['BOT_PREFIX'] = BOT_PREFIX
        settings['BOT_AVATAR'] = BOT_AVATAR
        settings['BOT_ACCENT_COLOR'] = BOT_ACCENT_COLOR
        settings['BOT_EMBED_FOOTER'] = BOT_EMBED_FOOTER
        settings['BOT_GAME_PRESENCE'] = BOT_GAME_PRESENCE
        settings['BOT_ADMIN_ROLE'] = BOT_ADMIN_ROLE
        settings['BOT_SERVICES_ALLOWED'] = BOT_SERVICES_ALLOWED
        settings['BOT_SERVICES_MAINTEINANCE'] = BOT_SERVICES_MAINTEINANCE
        settings['BOT_FEATURES_ENABLED'] = BOT_FEATURES_ENABLED
        settings['BOT_FEATURES_DISABLED'] = BOT_FEATURES_DISABLED
        settings['BOT_GATCHA']['GATCHA_CURRENT_PITY'] = GATCHA_CURRENT_PITY
        settings['BOT_GATCHA']['GATCHA_MAX_PITY'] = GATCHA_MAX_PITY
        settings['BOT_GATCHA']['GATCHA_50_50_LOOSE'] = GATCHA_50_50_LOOSE
        settings['BOT_VERSION'] = BOT_VERSION

        with open( 'src/configs/settings.json', 'w' ) as settingsFile:
            json.dump( settings, settingsFile, indent=4 )
            settingsFile.close()

        printStatus.success_green( "Configs updated successfully!", 2 )

    except Exception as e:
        printStatus.fail( "Error updating Configs: " + str(e), 1 )
        printStatus.warn( f"Settings update have failed, however {BOT_NAME} can continue to work, new settings will not be applied at next startup", 2 )

# Check if a Service is Running or Inactive/Failed
def checkService ( serviceName ):
    exit_code = os.system(f'systemctl is-active --quiet {serviceName}.service')
    if exit_code == 0:
        return "Running"

    else:
        return "Failed or Inactive"

# Check a Service and return a Human readable value
def checkServiceForHuman ( serviceName ):
    exit_code = os.system(f'systemctl is-active --quiet {serviceName}.service')
    if exit_code == 0:
        return f"{discordEmoji.DOT_GREEN} `Running`"

    else:
        return f"{discordEmoji.DOT_YELLOW} `Inactive` or {discordEmoji.DOT_RED} `Failed`"

# Check if a Feature is Enabled (1), Disabled (0) or doesn't exist (-1)
def checkFeature ( featureName ):
    global BOT_FEATURES_ENABLED, BOT_FEATURES_DISABLED
    if featureName in BOT_FEATURES_ENABLED:
        return 1

    elif featureName in BOT_FEATURES_DISABLED:
        return 0

    else:
        return -1

# Check a Feature and return a Human readable value
def checkFeatureForHuman ( featureName ):
    returned = checkFeature( featureName )
    if returned == 1:
        return f"{discordEmoji.DOT_GREEN} `Enabled`"

    elif returned == 0:
        return f"{discordEmoji.DOT_YELLOW} `Disabled`"

    elif returned == -1:
        return f"{discordEmoji.DOT_RED} `Inexistent`"

# Check if a message is sent by an Admin
def is_an_admin ( message ):
    global BOT_ADMIN_ROLE
    try:
        roles = [ discord.utils.get( message.guild.roles, name=BOT_ADMIN_ROLE ) ]
        for role in roles:
            if role in message.author.roles:
                return True
        
        return False

    except Exception:
        return False

# Infinite-Loop Functions to cycle Game Presence at random interval
async def update_game_presence ():
    global threadStopper, threadCondition
    with threadCondition:
        while not threadStopper.is_set():
            status = ""
            if checkFeature( 'minimal_mode' ) == 1:
                status = "[Minimal Mode] "

            status += f"{BOT_GAME_PRESENCE[random.randrange(0,len(BOT_GAME_PRESENCE))]}"
            await bot.change_presence( activity=discord.Game( name=status ) )
            threadCondition.wait( timeout=( random.randrange( 30, 60 ) ) )
##############################################
#                                            #
##############################################


##############################################
#              Bot Main Features             #
##############################################
@bot.event
async def on_ready():
    global guild_count
    printStatus.work( "Prepearing to list all Servers associated...", 1 )
    guild_count = 0
    for guild in bot.guilds:
        printStatus.info( f"Found Server: {guild.name} [ID: {guild.id}]", 2 )
        guild_count = guild_count + 1

    printStatus.info( f"{BOT_NAME} is in {str(guild_count)} guilds.", 2 )
    printStatus.success_green( "Servers list completed!", 1 )
    printStatus.work( "Setting Game Presence...", 1 )
    if BOT_GAME_PRESENCE == None:
        await bot.change_presence( activity=discord.Game( name="with " + str(guild_count) + " servers!" ) )
        printStatus.info( "Game Presence set to: with " + str(guild_count) + " servers!", 2 )

    else:
        threading.Thread( target=lambda: asyncio.set_event_loop( asyncio.new_event_loop().run_until_complete( update_game_presence() ) ) ).start()
        printStatus.info( f"Game Presence set to: {BOT_GAME_PRESENCE}", 2 )

    printStatus.success_green( "Game Presence set!", 1 )
    printStatus.success_green( f"{BOT_NAME} is now running!", 0 )

@bot.event
async def on_message( message ):
    global BOT_NAME, BOT_TOKEN, BOT_PREFIX, BOT_AVATAR, BOT_ACCENT_COLOR, BOT_EMBED_FOOTER, BOT_GAME_PRESENCE, BOT_ADMIN_ROLE, BOT_SERVICES_ALLOWED, BOT_SERVICES_MAINTEINANCE, BOT_FEATURES_ENABLED, BOT_FEATURES_DISABLED, GATCHA_CURRENT_PITY, GATCHA_MAX_PITY, GATCHA_50_50_LOOSE, BOT_VERSION, is_playing, is_paused, music_queue, loopStatus, threadStopper, threadCondition
    messageID = uuid.uuid1()

    if  checkFeature( 'loogger' ) == 1:
        await discordLogger.log( message )

    if BOT_PREFIX in message.content.split(" ")[0] or "sudo" in message.content.split(" ")[0] and message.author.id != bot.user.id:
        printStatus.work( f"[{messageID}] Potential command received from {message.author.name} [ID: {message.author.id}] -> {message.content}", 1 )

        # Help Message
        if message.content == f"{BOT_PREFIX}help":
            printStatus.info( f"[{messageID}] Command acknowledge [{BOT_PREFIX}help]", 2 )
            embed=discord.Embed(title=BOT_NAME, description=f"{BOT_NAME} can play music from YouTube and YouTube Music (with a little twist😉)!\nIt can also run custom services on Host Server through System Contol (A.K.A. `systemctl`)...", color=int(BOT_ACCENT_COLOR, 16))
            embed.set_thumbnail(url=BOT_AVATAR)
            embed.add_field(name=f"`{BOT_PREFIX}join`", value="Join your voice channel (if you are already in a voice channel)", inline=False)
            embed.add_field(name=f"`{BOT_PREFIX}preview <song name>`", value="Display what is the first result on YouTube", inline=False)
            embed.add_field(name=f"`{BOT_PREFIX}play <url | song name>`", value="Play a song from a link or a song name given", inline=False)
            embed.add_field(name=f"`{BOT_PREFIX}pause`", value="Pause the current song", inline=False)
            embed.add_field(name=f"`{BOT_PREFIX}resume`", value="Resume the song previously paused", inline=False)
            embed.add_field(name=f"`{BOT_PREFIX}skip`", value="Skip to the next song, if existing", inline=False)
            embed.add_field(name=f"`{BOT_PREFIX}loop <off | once | all>`", value="Enable/Disable song loop", inline=False)
            embed.add_field(name=f"`{BOT_PREFIX}stop`", value="Stop current song and flush the current queue", inline=False)
            embed.add_field(name=f"`{BOT_PREFIX}leave` | `{BOT_PREFIX}quit`", value="Leave the voice channel", inline=False)
            embed.add_field(name=f"`{BOT_PREFIX}pity`", value="T.m.y.f.a. ==> T.m.y.k.", inline=False)
            embed.add_field(name=f"`{BOT_PREFIX}dance`", value="`.webm` are very interesting...", inline=False)
            embed.add_field(name=f"`{BOT_PREFIX}systemctl <start | stop | restart | status> <service_name>`", value="System Control interface (Read also `" + BOT_PREFIX + "systemctl help` for more info)", inline=False)
            embed.add_field(name=f"`{BOT_PREFIX}minimal-mode`", value="Explain `Minimal Mode` and how does it work", inline=False)
            embed.set_footer(text=f"Version {BOT_VERSION} - {BOT_EMBED_FOOTER[random.randrange(0,len(BOT_EMBED_FOOTER))]}")
            await message.channel.send( embed=embed )
            printStatus.success_green( f"[{messageID}] Command executed", 1 )

        # Ping Command
        elif message.content == f"{BOT_PREFIX}ping":
            printStatus.info( f"[{messageID}] Command acknowledge [{BOT_PREFIX}ping]", 2 )
            await message.channel.send( f"Pong! in `{ round( ( datetime.now( timezone.utc ) - datetime.fromisoformat( str( message.created_at )  ).replace( tzinfo=timezone.utc ) ).total_seconds() * 1000, 1 ) } ms`", reference=message )
            printStatus.success_green( f"[{messageID}] Command executed", 1 )

        # Pong Command beacause why not
        elif message.content == f"{BOT_PREFIX}pong":
            printStatus.info( f"[{messageID}] Command acknowledge [{BOT_PREFIX}pong]", 2 )
            await message.channel.send( f"Are you trying to use my own spells against me, `{message.author.name}`?\nPathetic...", reference=message )
            printStatus.success_green( f"[{messageID}] Command executed", 1 )

        # Join to Voice Channel command
        elif message.content == f"{BOT_PREFIX}join" and checkFeature( 'music_player' ) == 1:
            printStatus.info( f"[{messageID}] Command acknowledge [{BOT_PREFIX}join]", 2 )
            voice = discord.utils.get( bot.voice_clients )
            if message.author.voice is not None:
                if voice == None:
                    await message.author.voice.channel.connect()
                    printStatus.success_green( f"[{messageID}] Command executed", 1 )

                else:
                    await message.channel.send("I'm already connected to a voice channel")
                    printStatus.warn( f"[{messageID}] Command not executed", 1 )

            else:
                await message.channel.send("You must be in a voice channel to use this command")
                printStatus.warn( f"[{messageID}] Command not executed", 1 )

            return

        # Leave Voice Channel command
        elif message.content == f"{BOT_PREFIX}leave" or message.content == f"{BOT_PREFIX}quit" and checkFeature( 'music_player' ) == 1:
            printStatus.info( f"[{messageID}] Command acknowledge [{BOT_PREFIX}leave]", 2 )
            voice = discord.utils.get( bot.voice_clients )
            if message.author.voice is not None:
                if voice == None:
                    await message.channel.send("I'm not connected to a voice channel")
                    printStatus.warn( f"[{messageID}] Command not executed", 1 )

                else:
                    if message.author.voice.channel == voice.channel:
                        await voice.disconnect()
                        printStatus.success_green( f"[{messageID}] Command executed", 1 )

                    else:
                        await message.channel.send("You are not in my voice channel")
                        printStatus.warn( f"[{messageID}] Command not executed", 1 )

            else:
                await message.channel.send("You must be in a voice channel to use this command")
                printStatus.warn( f"[{messageID}] Command not executed", 1 )

            return

        # Preview command
        elif f"{BOT_PREFIX}preview " in message.content and checkFeature( 'music_player' ) == 1:
            printStatus.info( f"[{messageID}] Command acknowledge [{BOT_PREFIX}preview]", 2 )
            if len( message.content.split(' ') ) >= 2:
                if not "youtube.com/watch?v=" in message.content.split(' ')[1]:
                    async with message.channel.typing():
                        url = search( message.content.split(' ')[1] )["webpage_url"]
                        url_info = ytdl.extract_info(url, download=False)
                        await message.channel.send(f"Result for this query is:\n**Title**: `{url_info['title']}`\n**Duration**: `{str(timedelta(seconds=url_info['duration']))}`\n**Link**: {url}", reference=message)

                else:
                    await message.channel.send(f"Invalid query: `no link accepted`", reference=message)

            else:
                await message.channel.send(f"Invalid query: `query string not inserted`", reference=message)
            printStatus.success_green( f"[{messageID}] Command executed", 1 )

        # Play Music command
        elif f"{BOT_PREFIX}play" in message.content and checkFeature( 'music_player' ) == 1:
            printStatus.info( f"[{messageID}] Command acknowledge [{BOT_PREFIX}play]", 2 )
            voice = discord.utils.get( bot.voice_clients )
            if message.author.voice == None:
                await message.channel.send("You must be in a voice channel to use this command")
                printStatus.warn( f"[{messageID}] Command not executed", 1 )
                return

            elif voice != None and message.author.voice.channel != voice.channel:
                await message.channel.send("You are not in my voice channel")
                printStatus.warn( f"[{messageID}] Command not executed", 1 )
                return

            if loopStatus == "once":
                await message.channel.send("Loop is set to `once`, no further songs will be accepted", reference=message)
                printStatus.warn( f"[{messageID}] Command not executed", 1 )
                return

            GATCHA_CURRENT_PITY += 1
            async with message.channel.typing():
                searching = await message.channel.send( f"{discordEmoji.MAGNIFIER} Searching for the song...", reference=message )
                if "youtube.com/watch?v=" in message.content:
                    message.content.replace("music.youtube", "youtube")
                    url = message.content.split(' ')[1]

                else:
                    url = search( message.content.replace( f"{BOT_PREFIX}play ", '' ) )["webpage_url"]

                if checkFeature( 'pity' ) == 1:
                    if random.randrange( 0, GATCHA_MAX_PITY - GATCHA_CURRENT_PITY ) == 0 or GATCHA_CURRENT_PITY >= GATCHA_MAX_PITY:
                        GATCHA_CURRENT_PITY = 0
                        url = GATCHA_50_50_LOOSE[ random.randrange( 0, len( GATCHA_50_50_LOOSE ) ) ][1]

                url_info = ytdl.extract_info(url, download=False)

                audio_player = None

                if checkFeature( 'caching' ) == 1:
                    if url_info['duration'] <= 900:
                        if SELECT( BUFFER_JSON, "webpage_id", id_from_url( url ), 0 ) != None:
                            temp = SELECT( BUFFER_JSON, "webpage_id", id_from_url( url ), 1 )
                            audio_player = discord.FFmpegPCMAudio( f"{BUFFER_DIR}{temp['uuid']}.mp3" )
                            music_queue.append( [ audio_player, url_info['title'], True, temp['uuid'] ] )

                        else:
                            loopBuffer = asyncio.new_event_loop()
                            tempUUID = uuid.uuid1()
                            await message.channel.send(f"{discordEmoji.WARNING} Song **{url_info['title']}** not in cache, fast buffering in background while streaming...", reference=message)
                            loopBuffer.run_in_executor( None, fastBuffer, str( tempUUID ), url )
                            INSERT( BUFFER_JSON, [ id_from_url( url ), url_info['title'], str( tempUUID ), False ] )
                            audio_player = discord.FFmpegPCMAudio( url_info['url'] )
                            music_queue.append( [ audio_player, url_info['title'], False, str( tempUUID ) ] )

                    else:
                        await message.channel.send(f"{discordEmoji.WARNING} Song **{url_info['title']}** too long, only streaming allowed", reference=message)
                        audio_player = discord.FFmpegPCMAudio( url_info['url'] )
                        music_queue.append( [ audio_player, url_info['title'], False, None ] )
                
                else:
                    url_info = ytdl.extract_info(url, download=False)
                    audio_player = discord.FFmpegPCMAudio( url_info['url'] )
                    music_queue.append( [ audio_player, url_info['title'], False, None ] )

                updateSettings()

                await searching.delete()

            if not is_playing:
                is_playing = True
                await play_next_song( message )

            else:
                await message.channel.send(f"{discordEmoji.RADIO} Song added to queue ( **{url_info['title']}** )", reference=message)


            printStatus.success_green( f"[{messageID}] Command executed", 1 )
            return

        # Pause Music command
        elif message.content == f"{BOT_PREFIX}pause" and checkFeature( 'music_player' ) == 1:
            printStatus.info( f"[{messageID}] Command acknowledge [{BOT_PREFIX}pause]", 2 )
            voice = discord.utils.get( bot.voice_clients )
            if voice == None:
                await message.channel.send("I'm not playing anything")
                printStatus.warn( f"[{messageID}] Command not executed", 1 )

            else:
                if not is_paused:
                    is_paused = True
                    vc.pause()
                    await message.channel.send( f"{discordEmoji.BUTTON_PAUSE} Paused", reference=message )
                printStatus.success_green( f"[{messageID}] Command executed", 1 )

            return

        # Resume Music command
        elif message.content == f"{BOT_PREFIX}resume" and checkFeature( 'music_player' ) == 1:
            printStatus.info( f"[{messageID}] Command acknowledge [{BOT_PREFIX}resume]", 2 )
            voice = discord.utils.get( bot.voice_clients )
            if voice == None:
                await message.channel.send("There is nothing to play")
                printStatus.warn( f"[{messageID}] Command not executed", 1 )

            else:
                if is_paused:
                    is_paused = False
                    vc.resume()
                    await message.channel.send( f"{discordEmoji.BUTTON_PLAY} Resumed", reference=message )
                printStatus.success_green( f"[{messageID}] Command executed", 1 )

            return

        # Skip Music command
        elif message.content == f"{BOT_PREFIX}skip" and checkFeature( 'music_player' ) == 1:
            printStatus.info( f"[{messageID}] Command acknowledge [{BOT_PREFIX}stop]", 2 )
            if is_playing:
                vc.stop()

            printStatus.success_green( f"[{messageID}] Command executed", 1 )

        # Stop Music command
        elif message.content == f"{BOT_PREFIX}stop" and checkFeature( 'music_player' ) == 1:
            printStatus.info( f"[{messageID}] Command acknowledge [{BOT_PREFIX}stop]", 2 )
            voice = discord.utils.get( bot.voice_clients )
            if voice == None:
                await message.channel.send("I'm not playing anything")
                printStatus.warn( f"[{messageID}] Command not executed", 1 )

            else:
                voice.stop()
                music_queue = []
                await message.channel.send( f"{discordEmoji.BUTTON_STOP} Stopped", reference=message )
                printStatus.success_green( f"[{messageID}] Command executed", 1 )

            return

        # Loop Queue command
        elif f"{BOT_PREFIX}loop " in message.content and checkFeature( 'music_player' ) == 1:
            printStatus.info( f"[{messageID}] Command acknowledge [{BOT_PREFIX}loop]", 2 )
            if message.content.split(' ')[1] == "off" or message.content.split(' ')[1] == "once" or message.content.split(' ')[1] == "all":
                await message.channel.send( f"{discordEmoji.REPEAT} Loop modifier set to: `{message.content.split(' ')[1]}`" )
                loopStatus = message.content.split(' ')[1]

            else:
                await message.channel.send( f"{discordEmoji.THINKING_FACE} Loop modifier not recognized...", reference=message )

            printStatus.success_green( f"[{messageID}] Command executed", 1 )
            return

        # Check Pity command
        elif f"{BOT_PREFIX}pity" in message.content and checkFeature( 'pity' ) == 1:
            printStatus.info( f"[{messageID}] Command acknowledge [{BOT_PREFIX}pity]", 2 )
            await message.channel.send( f"{discordEmoji.DICE} Current Pity is {GATCHA_CURRENT_PITY}/{GATCHA_MAX_PITY}...", reference=message )
            printStatus.success_green( f"[{messageID}] Command executed", 1 )
            return

        # System Control command
        elif f"{BOT_PREFIX}systemctl " in message.content and checkFeature( 'systemctl' ) == 1:
            if checkFeature( 'minimal_mode' ) == 0:
                if message.content == f"{BOT_PREFIX}systemctl help":
                    printStatus.info( f"[{messageID}] Command acknowledge [{BOT_PREFIX}systemctl help]", 2 )
                    embed=discord.Embed(title=f"{BOT_NAME} | {BOT_PREFIX}systemctl help", description=f"List of accepted services:", color=int(BOT_ACCENT_COLOR, 16))
                    embed.set_thumbnail(url=BOT_AVATAR)
                    if BOT_SERVICES_ALLOWED != []:
                        for service in BOT_SERVICES_ALLOWED:
                            embed.add_field(name=f"`{service}`", value="Service allowed", inline=True)
                    if BOT_SERVICES_MAINTEINANCE != []:
                        for service in BOT_SERVICES_MAINTEINANCE:
                            embed.add_field(name=f"`{service}`", value="Service under mainteinance", inline=True)
                    embed.set_footer(text=f"Version {BOT_VERSION} - {BOT_EMBED_FOOTER[random.randrange(0,len(BOT_EMBED_FOOTER))]}")
                    await message.channel.send(embed=embed, reference=message)
                    printStatus.success_green( f"[{messageID}] Command executed", 1 )
                    return

                elif f"{BOT_PREFIX}systemctl start" in message.content and len( message.content.split(' ') ) == 3:
                    service = message.content.split(' ')[2].replace(".service", '')
                    printStatus.info( f"[{messageID}] Command acknowledge [{BOT_PREFIX}systemctl start {service}]", 2 )
                    async with message.channel.typing():
                        if service in BOT_SERVICES_ALLOWED:
                            if checkService( service ) != "Running":
                                initialMessage = await message.channel.send(f"{discordEmoji.DOT_YELLOW} Initializing `{service}.service`...", reference=message)
                                os.system( f"sudo ./pythonSystemctl.sh start {service}" )
                                await initialMessage.delete()
                                await message.channel.send( f"{discordEmoji.DOT_GREEN} `{service}.service` is now running...", reference=message )

                            else:
                                await message.channel.send( f"{discordEmoji.DOT_YELLOW} Service `{service}.service` is already running" )

                        elif service in BOT_SERVICES_MAINTEINANCE:
                            await message.channel.send(f"{discordEmoji.DOT_YELLOW} Service `{service}.service` is currently under maintenance, try later...", reference=message)

                        else:
                            await message.channel.send(f"{discordEmoji.DOT_RED} Service `{service}.service` is not allowed for the moment...", reference=message)

                    printStatus.success_green( f"[{messageID}] Command executed", 1 )
                    return

                elif f"{BOT_PREFIX}systemctl stop" in message.content and len( message.content.split(' ') ) == 3:
                    service = message.content.split(' ')[2].replace(".service", '')
                    printStatus.info( f"[{messageID}] Command acknowledge [{BOT_PREFIX}systemctl stop {service}]", 2 )
                    async with message.channel.typing():
                        if service in BOT_SERVICES_ALLOWED:
                            initialMessage = await message.channel.send(f"{discordEmoji.DOT_YELLOW} Stopping `{service}.service`...", reference=message)
                            os.system( f"sudo ./pythonSystemctl.sh stop {service}" )
                            await initialMessage.delete()
                            await message.channel.send( f"{discordEmoji.DOT_GREEN} `{service}.service` stopped", reference=message )

                        elif service in BOT_SERVICES_MAINTEINANCE:
                            await message.channel.send(f"{discordEmoji.DOT_YELLOW} Service `{service}.service` is currently under maintenance, try later...", reference=message)

                        else:
                            await message.channel.send(f"{discordEmoji.DOT_RED} Service `{service}.service` is not allowed for the moment...", reference=message)

                    printStatus.success_green( f"[{messageID}] Command executed", 1 )
                    return

                elif f"{BOT_PREFIX}systemctl restart" in message.content and len( message.content.split(' ') ) == 3:
                    service = message.content.split(' ')[2].replace(".service", '')
                    printStatus.info( f"[{messageID}] Command acknowledge [{BOT_PREFIX}systemctl restart {service}]", 2 )
                    async with message.channel.typing():
                        if service in BOT_SERVICES_ALLOWED:
                            initialMessage = await message.channel.send(f"{discordEmoji.DOT_YELLOW} Restarting `{service}.service`...", reference=message)
                            os.system( f"sudo ./pythonSystemctl.sh restart {service}" )
                            await initialMessage.delete()
                            await message.channel.send( f"{discordEmoji.DOT_GREEN} `{service}.service` restarted...", reference=message )

                        elif service in BOT_SERVICES_MAINTEINANCE:
                            await message.channel.send(f"{discordEmoji.DOT_YELLOW} Service `{service}.service` is currently under maintenance, try later...", reference=message)

                        else:
                            await message.channel.send(f"{discordEmoji.DOT_RED} Service `{service}.service` is not allowed for the moment...", reference=message)

                    printStatus.success_green( f"[{messageID}] Command executed", 1 )
                    return

                elif f"{BOT_PREFIX}systemctl status" in message.content and len( message.content.split(' ') ) == 3:
                    service = message.content.split(' ')[2].replace(".service", '')
                    printStatus.info( f"[{messageID}] Command acknowledge [{BOT_PREFIX}systemctl status {service}]", 2 )
                    async with message.channel.typing():
                        if service in BOT_SERVICES_ALLOWED:
                            await message.channel.send( f"`{service}.service` status: {checkServiceForHuman( service )}", reference=message )

                        elif service in BOT_SERVICES_MAINTEINANCE:
                            await message.channel.send(f"{discordEmoji.DOT_YELLOW} Service `{service}.service` is currently under maintenance, try later...", reference=message)

                        else:
                            await message.channel.send(f"{discordEmoji.DOT_RED} Service `{service}.service` is not allowed for the moment...", reference=message)

                    printStatus.success_green( f"[{messageID}] Command executed", 1 )
                    return

                else:
                    await message.channel.send( f"Unknown command, use `{BOT_PREFIX}systemctl help`" )

            else:
                await message.channel.send(f"{discordEmoji.DOT_RED} System Control is disabled when in `[Minimal Mode]`.\n\t\tFurther info at `{BOT_PREFIX}minimal-mode`", reference=message)

        # sudo Section
        elif "sudo " in message.content:
            if is_an_admin( message ):
                if message.content == "sudo help":
                    printStatus.info( f"[{messageID}] Command acknowledge [sudo help]", 2 )
                    embed=discord.Embed(title=f"{BOT_NAME} | `sudo help`", description=f"`sudo` manual:", color=int(BOT_ACCENT_COLOR, 16))
                    embed.set_thumbnail(url=BOT_AVATAR)
                    embed.add_field(name=f"`sudo restart now`", value="Restart the bot (Only if the Host Service have the `Restart` flag set to always)", inline=False)
                    embed.add_field(name=f"`sudo reset`", value="Overwrite the `setting.json` with `resetSettings.json` and reload settings", inline=False)
                    embed.add_field(name=f"`sudo buffer [wipe]`", value="Wipe the song Buffer", inline=False)
                    embed.add_field(name=f"`sudo tweak [prefix | admin] <new_prefix | new_admin>`", value="Tweak some basic variables", inline=False)
                    embed.add_field(name=f"`sudo settings <update | reload>`", value="Refresh the Bot settings", inline=False)
                    embed.add_field(name=f"`sudo [enable | disable] [feature | service] <name>`", value="Enable/Disable Feature/Service", inline=False)
                    embed.add_field(name=f"`sudo eval <arg>`", value="Evaluate passed python code", inline=False)
                    embed.set_footer(text=f"Version {BOT_VERSION} - {BOT_EMBED_FOOTER[random.randrange(0,len(BOT_EMBED_FOOTER))]}")
                    await message.channel.send(embed=embed, reference=message)
                    printStatus.success_green( f"[{messageID}] Command executed", 1 )
                    return

                # Factory Reset
                elif message.content == "sudo reset":
                    printStatus.info( f"[{messageID}] Command acknowledge [sudo reset]", 2 )
                    async with message.channel.typing():
                        initialMessage = await message.channel.send("Returning to Factory Settings...")
                        importConfigs( source='reset' )

                    
                        await initialMessage.delete()
                        await message.channel.send( f"{discordEmoji.BLUE_CHECK} Factory Settings restored", reference=message )
                        importConfigs( additionalTab=1 )
                    printStatus.fail( f"[{messageID}] Command not executed", 1 )
                    return

                # Bot restart control
                elif message.content == "sudo restart now":
                    printStatus.info( f"[{messageID}] Command acknowledge [sudo restart now]", 2 )
                    async with message.channel.typing():
                        await message.channel.send(f"Restarting {BOT_NAME}...")
                        try:
                            threadStopper.set()
                            with threadCondition:
                                threadCondition.notify()

                        except Exception:
                            pass

                    printStatus.success_green( f"[{messageID}] Command executed", 1 )
                    exit( 0 )
                    return

                # Buffer control
                elif "sudo buffer " in message.content:
                    if " wipe" in message.content:
                        printStatus.info( f"[{messageID}] Command acknowledge [sudo buffer wipe]", 2 )
                        async with message.channel.typing():
                            initialMessage = await message.channel.send("Wiping Buffer...")
                            wipe_buffer()
                            await initialMessage.delete()
                            await message.channel.send( f"{discordEmoji.BLUE_CHECK} Buffer Wiped", reference=message )
                            importConfigs( additionalTab=1 )
                        printStatus.success_green( f"[{messageID}] Command executed", 1 )
                        return

                    else:
                        await message.channel.send( f"Improper use of `sudo` command (Command not found)" )
                        return

                # Tweaks control
                elif "sudo tweak " in message.content:
                    if " prefix" in message.content:
                        printStatus.info( f"[{messageID}] Command acknowledge [sudo tweak prefix]", 2 )
                        if len( message.content.replace( "sudo tweak prefix ", "" ).split(" ") ) == 1:
                            BOT_PREFIX = message.content.replace( "sudo tweak prefix ", "" )
                            updateSettings()
                            await message.channel.send( f"{discordEmoji.BLUE_CHECK} Prefix Updated to `{BOT_PREFIX}`", reference=message )
                            printStatus.success_green( f"[{messageID}] Command executed", 1 )
                            return

                        else:
                            await message.channel.send( f"{discordEmoji.DOT_RED} `{BOT_PREFIX}` is **NOT** a valid prefix!", reference=message )
                            printStatus.fail( f"[{messageID}] Command not executed", 1 )
                            return

                    elif " admin" in message.content:
                        printStatus.info( f"[{messageID}] Command acknowledge [sudo tweak admin]", 2 )
                        if len( message.content.replace( "sudo tweak admin ", "" ).split(" ") ) == 1:
                            BOT_ADMIN_ROLE = message.content.replace( "sudo tweak admin ", "" )
                            updateSettings()
                            await message.channel.send( f"{discordEmoji.BLUE_CHECK} Admin Role Updated to `{BOT_ADMIN_ROLE}`", reference=message )
                            printStatus.success_green( f"[{messageID}] Command executed", 1 )
                            return

                        else:
                            await message.channel.send( f"{discordEmoji.DOT_RED} `{BOT_PREFIX}` is **NOT** a valid prefix!", reference=message )
                            printStatus.fail( f"[{messageID}] Command not executed", 1 )
                            return

                    else:
                        await message.channel.send( f"Improper use of `sudo` command (Command not found)" )
                        return

                # Settings control
                elif "sudo settings " in message.content:
                    if " update" in message.content:
                        printStatus.info( f"[{messageID}] Command acknowledge [sudo settings update]", 2 )
                        async with message.channel.typing():
                            initialMessage = await message.channel.send("Updating Settings...")
                            updateSettings()
                            await initialMessage.delete()
                            await message.channel.send( f"{discordEmoji.BLUE_CHECK} Settings Updated", reference=message )
                            importConfigs( additionalTab=1 )
                        printStatus.success_green( f"[{messageID}] Command executed", 1 )
                        return

                    elif " reload" in message.content:
                        printStatus.info( f"[{messageID}] Command acknowledge [sudo settings reload]", 2 )
                        async with message.channel.typing():
                            initialMessage = await message.channel.send("Reloading Settings...")
                            importConfigs()
                            await initialMessage.delete()
                            await message.channel.send( f"{discordEmoji.BLUE_CHECK} Settings Reloaded", reference=message )
                            importConfigs( additionalTab=1 )
                        printStatus.success_green( f"[{messageID}] Command executed", 1 )
                        return

                    else:
                        await message.channel.send( f"Improper use of `sudo` command (Command not found)" )
                        return

                # Services/Features Enabler
                elif "sudo enable " in message.content:
                    if "sudo enable service " in message.content:
                        printStatus.info( f"[{messageID}] Command acknowledge [sudo enable service]", 2 )
                        async with message.channel.typing():
                            serviceName = message.content.replace("sudo enable service ", "").split(" ")[0].replace(".service", "")
                            if serviceName in BOT_SERVICES_MAINTEINANCE:
                                BOT_SERVICES_ALLOWED.append( serviceName )
                                BOT_SERVICES_MAINTEINANCE.remove( serviceName )
                                await message.channel.send( f"{discordEmoji.DOT_GREEN} Service `{serviceName}.service` **enabled**", reference=message )
                                printStatus.success_green( f"[{messageID}] Command executed", 1 )
                                return

                            elif serviceName not in BOT_SERVICES_ALLOWED and serviceName not in BOT_SERVICES_MAINTEINANCE:
                                await message.channel.send( f"{discordEmoji.DOT_RED} Service `{serviceName}.service` **unavailable**", reference=message )
                                printStatus.fail( f"[{messageID}] Command not executed", 1 )
                                return

                    elif "sudo enable feature " in message.content:
                        printStatus.info( f"[{messageID}] Command acknowledge [sudo feature service]", 2 )
                        async with message.channel.typing():
                            serviceName = message.content.replace("sudo enable feature ", "").split(" ")[0]
                            if serviceName in BOT_FEATURES_DISABLED:
                                BOT_FEATURES_ENABLED.append( serviceName )
                                BOT_FEATURES_DISABLED.remove( serviceName )
                                await message.channel.send( f"{discordEmoji.DOT_GREEN} Feature `{serviceName}` **enabled**", reference=message )
                                printStatus.success_green( f"[{messageID}] Command executed", 1 )
                                return

                            elif serviceName not in BOT_FEATURES_ENABLED and serviceName not in BOT_FEATURES_DISABLED:
                                await message.channel.send( f"{discordEmoji.DOT_RED} Feature `{serviceName}` **unavailable**", reference=message )
                                printStatus.fail( f"[{messageID}] Command not executed", 1 )
                                return

                    else:
                        await message.channel.send( f"Improper use of `sudo` command (Command not found)" )
                        return

                # Services/Features Disabler
                elif "sudo disable " in message.content:
                    if "sudo disable service " in message.content:
                        printStatus.info( f"[{messageID}] Command acknowledge [sudo disable service]", 2 )
                        async with message.channel.typing():
                            serviceName = message.content.replace("sudo disable service ", "").split(" ")[0].replace(".service", "")
                            if serviceName in BOT_SERVICES_ALLOWED:
                                BOT_SERVICES_MAINTEINANCE.append( serviceName )
                                BOT_SERVICES_ALLOWED.remove( serviceName )
                                await message.channel.send( f"{discordEmoji.DOT_GREEN} Service `{serviceName}.service` **disabled**", reference=message )
                                printStatus.success_green( f"[{messageID}] Command executed", 1 )
                                return

                            elif serviceName not in BOT_SERVICES_ALLOWED and serviceName not in BOT_SERVICES_MAINTEINANCE:
                                await message.channel.send( f"{discordEmoji.DOT_RED} Service `{serviceName}.service` **unavailable**", reference=message )
                                printStatus.fail( f"[{messageID}] Command not executed", 1 )
                                return

                    elif "sudo disable feature " in message.content:
                        printStatus.info( f"[{messageID}] Command acknowledge [sudo disable feature]", 2 )
                        async with message.channel.typing():
                            serviceName = message.content.replace("sudo disable feature ", "").split(" ")[0]
                            if serviceName in BOT_FEATURES_ENABLED:
                                BOT_FEATURES_DISABLED.append( serviceName )
                                BOT_FEATURES_ENABLED.remove( serviceName )
                                await message.channel.send( f"{discordEmoji.DOT_GREEN} Feature `{serviceName}` **disabled**", reference=message )
                                printStatus.success_green( f"[{messageID}] Command executed", 1 )
                                return

                            elif serviceName not in BOT_FEATURES_ENABLED and serviceName not in BOT_FEATURES_DISABLED:
                                await message.channel.send( f"{discordEmoji.DOT_RED} Feature `{serviceName}` **unavailable**", reference=message )
                                printStatus.fail( f"[{messageID}] Command not executed", 1 )
                                return

                    else:
                        await message.channel.send( f"Improper use of `sudo` command (Command not found)" )
                        return

                # Services Creator and Remover
                elif "sudo service " in message.content:
                    if "sudo service create " in message.content:
                        printStatus.info( f"[{messageID}] Command acknowledge [sudo service create]", 2 )
                        async with message.channel.typing():
                            serviceName = message.content.replace("sudo service create ", "").split(" ")[0].replace(".service", "")
                            if serviceName in BOT_SERVICES_ALLOWED:
                                await message.channel.send( f"{discordEmoji.DOT_RED} Service `{serviceName}.service` already exist and is `Enabled`", reference=message )
                                printStatus.fail( f"[{messageID}] Command not executed", 1 )
                                return

                            elif serviceName in BOT_SERVICES_MAINTEINANCE:
                                await message.channel.send( f"{discordEmoji.DOT_RED} Service `{serviceName}.service` already exist and is `Disabled`", reference=message )
                                printStatus.fail( f"[{messageID}] Command not executed", 1 )
                                return

                            else:
                                BOT_SERVICES_MAINTEINANCE.append( serviceName )
                                await message.channel.send( f"{discordEmoji.DOT_GREEN} Service `{serviceName}.service` created and now is `Disabled`\nRun `sudo enable service {serviceName}` to enable it", reference=message )
                                printStatus.succes_green( f"[{messageID}] Command executed", 1 )
                                return

                    elif "sudo service remove " in message.content:
                        printStatus.info( f"[{messageID}] Command acknowledge [sudo service remove]", 2 )
                        async with message.channel.typing():
                            serviceName = message.content.replace("sudo service remove ", "").split(" ")[0].replace(".service", "")
                            if serviceName in BOT_SERVICES_ALLOWED or serviceName in BOT_SERVICES_MAINTEINANCE:
                                if serviceName in BOT_SERVICES_ALLOWED:
                                    BOT_SERVICES_ALLOWED.remove( serviceName )

                                if serviceName in BOT_SERVICES_MAINTEINANCE:
                                    BOT_SERVICES_MAINTEINANCE.remove( serviceName )

                                await message.channel.send( f"{discordEmoji.DOT_GREEN} Service `{serviceName}.service` removed", reference=message )
                                printStatus.success_green( f"[{messageID}] Command executed", 1 )
                                return

                            else:
                                await message.channel.send( f"{discordEmoji.DOT_RED} Service `{serviceName}.service` doesn't exist", reference=message )
                                printStatus.fail( f"[{messageID}] Command not executed", 1 )
                                return

                    else:
                        await message.channel.send( f"Improper use of `sudo` command (Command not found)" )
                        return

                # Raw Code evaluation
                elif "sudo eval " in message.content:
                    printStatus.info( f"[{messageID}] Command acknowledge [sudo eval]", 2 )
                    await message.channel.send( f"{ eval( message.content.replace( 'sudo eval ', '' ) ) }" )
                    printStatus.success_green( f"[{messageID}] Command executed", 1 )
                    return

                else:
                    await message.channel.send( f"Improper use of `sudo` command (Command not found)" )

            else:
                await message.channel.send(f"{discordEmoji.DOT_RED} You don't have `sudo` privileges, this incident will be reported...", reference=message)


        # Fun command
        elif message.content == f"{BOT_PREFIX}dance":
            printStatus.info( f"[{messageID}] Command acknowledge [{BOT_PREFIX}dance]", 2 )
            async with message.channel.typing():
                with open( 'src/configs/pre-built.json', 'r' ) as source:
                    fun = json.load( source )
                    source.close()
                    await message.channel.send( fun["dance"][ random.randrange( 0, len( fun["dance"] ) ) ] )


            printStatus.success_green( f"[{messageID}] Command executed", 1 )
            return

        # Minimal Mode info
        elif f"{BOT_PREFIX}minimal-mode" in message.content:
            printStatus.info( f"[{messageID}] Command acknowledge [{BOT_PREFIX}minimal-mode]", 2 )
            await message.channel.send(f"In `[Minimal Mode]` {BOT_NAME} will not have the following features:\n- System Control (A.K.A. `{BOT_PREFIX}systemctl`)\n\nIs {BOT_NAME} in `[Minimal Mode]`? {checkFeatureForHuman( 'minimal_mode' )}", reference=message)
            pass
##############################################
#                                            #
##############################################


if __name__ == '__main__':
    printStatus.work( "Checking if Settings need an update...", 0 )
    for fileConf in [ 'src/configs/settings.json', 'src/configs/resetSettings.json' ]:
        printStatus.work( f"Checking '{ fileConf }'...", 1 )
        if fileExists( fileConf + ".new" ) and fileExists( fileConf ):
            printStatus.info( f"Updating old '{ fileConf }'...", 2 )
            oldConf = []
            newConf = []
            with open( fileConf, "r" ) as external_Conf:
                oldConf = json.load( external_Conf )
                external_Conf.close()

            with open( fileConf + ".new", "r" ) as external_Conf:
                newConf = json.load( external_Conf )
                external_Conf.close()

            for service in newConf["BOT_FEATURES_DISABLED"]:
                try:
                    if service not in oldConf["BOT_FEATURES_ENABLED"] and service not in oldConf["BOT_FEATURES_DISABLED"]:
                        oldConf["BOT_FEATURES_DISABLED"].append( service )
                        printStatus.info( f"Added new service '{ service }'", 1 )

                except Exception:
                    pass

            try:
                oldConf["BOT_VERSION"] = newConf["BOT_VERSION"]
                printStatus.info( f"Updated to version '{ newConf['BOT_VERSION'] }'", 1 )

            except Exception:
                pass

            with open( fileConf, "w" ) as external_Conf:
                json.dump( oldConf, external_Conf, indent=4 )
                external_Conf.close()

            remove( fileConf + ".new" )

        elif fileExists( fileConf + ".new" ) and not fileExists( fileConf ):
            printStatus.info( f"Creating '{ fileConf }'...", 1 )
            rename( fileConf + ".new" , fileConf )

        printStatus.success_green( "Done", 1 )

    printStatus.success_green( "Done", 0 )

    printStatus.work( "Bot is starting up...", 0 )
    importConfigs()
    bot.run( BOT_TOKEN )