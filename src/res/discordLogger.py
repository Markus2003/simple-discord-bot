import json
from datetime import datetime
from os.path import exists as fileExists

import discord


def timeLog():
    return f"{datetime.now().date().day}/{datetime.now().date().month}/{datetime.now().date().year} - {datetime.now().hour}:{datetime.now().minute}:{datetime.now().second}"

async def log ( message ):
    log = {"dm": {}, "server": {}}
    if not fileExists( 'src/logger.json' ):
        with open( 'src/logger.json', 'w' ) as logger:
                json.dump( log, logger, indent=4)
                logger.close()

    with open( 'src/logger.json', 'r' ) as logger:
        log = json.load( logger )
        logger.close()

    if isinstance( message.channel, discord.channel.DMChannel):
        container_message = {
            "message_id": f"{message.id}",
            "timestamp": timeLog(),
            "author_name": f"{message.author.name}",
            "author_id": f"{message.author.id}",
            "content": f"{message.content}"
        }
        try:
            log["dm"][f"{message.channel.id}"].append( container_message )

        except Exception:
            log["dm"][f"{message.channel.id}"] = []
            log["dm"][f"{message.channel.id}"].append( container_message )

    else:
        container_message = {
            "message_id": f"{message.id}",
            "timestamp": timeLog(),
            "author_name": f"{message.author.name}",
            "author_nickname": f"{message.author.nick}",
            "author_id": f"{message.author.id}",
            "content": f"{message.content}"
        }
        try:
            log["server"][f"{message.guild.id} - {message.guild.name}"][f"{message.channel.id} - {message.channel.name}"].append( container_message )

        except Exception:
            try:
                log["server"][f"{message.guild.id} - {message.guild.name}"][f"{message.channel.id} - {message.channel.name}"] = []
                log["server"][f"{message.guild.id} - {message.guild.name}"][f"{message.channel.id} - {message.channel.name}"].append( container_message )

            except Exception:
                log["server"][f"{message.guild.id} - {message.guild.name}"] = {}
                log["server"][f"{message.guild.id} - {message.guild.name}"][f"{message.channel.id} - {message.channel.name}"] = []
                log["server"][f"{message.guild.id} - {message.guild.name}"][f"{message.channel.id} - {message.channel.name}"].append( container_message )

    with open( 'src/logger.json', 'w' ) as logger:
        json.dump( log, logger, indent=4)
        logger.close()