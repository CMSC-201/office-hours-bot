import json
import logging
import os

import discord
from discord import Message, Guild, CategoryChannel

import command as com

logger = logging.getLogger('bot_main')


class MyClient(discord.Client):
    def __init__(self, **options):
        super().__init__(**options)

    async def on_ready(self):
        logger.info('Logged on as {0}!'.format(self.user))

    async def on_message(self, message: Message):
        # if message.content.startswith('hashbot'):
        #    await message.channel.send('https://gph.is/28LBdcE')
        guild: Guild = message.guild
        logger.info('Message from {0.author}: {0.content}'.format(message))
        users_mentioned_in_role = []
        for role in message.role_mentions:
            users_mentioned_in_role.extend(role.members)

        if self.user in message.mentions or self.user in users_mentioned_in_role:
            if "set up" in message.content or "setup" in message.content:
                await self.setup(guild, message)
            else:
                # If nothing else, do this
                await message.channel.send("Yes?")

        # Ignore bot messages
        if message.author.bot:
            return
        # Split message by spaces
        args = com.parse_arguments(message, prefix)
        # If not a command, ignore
        if not args:

            return

        logger.info('{0.author} issued command: {0.content}'.format(message))
        response = com.execute_command(message, args, uuids)
        if response:
            logger.info(response)

    async def setup(self, guild: Guild, message: Message):
        if "Bulletin Board" in [c.name for c in guild.categories]:
            await message.channel.send(
                "Foolish mortal, we are already prepared! " +
                "Delete the Bulletin Board category if you want to remake the world!")
            return

        for channel in guild.channels:
            await channel.delete()

        channel_structure = {
            "Bulletin Board": {
                "text": ["landing-pad", "getting-started", "announcements", "authentication"],
                "voice": [],
            },
            "Instructor's Area": {
                "text": ["course-staff-general", "student"],
                "voice": ["instructor-lounge", "ta-lounge"],
            },
            "Student's Area": {
                "text": ["general", "tech-support", "memes", "waiting-room"],
                "voice": ["questions"],
            }
        }
        first = None

        for category, channels in channel_structure.items():
            text, voice = (channels["text"], channels["voice"])
            category_channel: CategoryChannel = await guild.create_category(category)

            for name in text:
                channel = await category_channel.create_text_channel(name)
                if not first:
                    first = channel
                logger.info("Created text channel {} in category {}".format(name, category))

            for name in voice:
                await category_channel.create_voice_channel(name)
                logger.info("Created voice channel {} in category {}".format(name, category))



        await first.send("Righto! You're good to go, boss!")


def get_globals():
    global token
    global prefix
    global uuids

    info = {}
    if os.path.exists('../uuids.json'):
        with open('../uuids.json', 'r') as f:
            info['uuids'] = json.load(f)
    else:
        info['uuids'] = {}

    if os.path.exists('../prop.json'):
        with open('../prop.json', 'r') as f:
            info['props'] = json.load(f)
    else:
        info['props'] = {
            "token": os.environ.get("BOT_TOKEN"),
            "prefix": os.environ.get("BOT_PREFIX"),
            "mongodb-address": os.environ.get("MONGODB_ADDRESS"),
        }
    return info


def set_up_logs():
    FORMAT = '%(asctime)s:%(levelname)s:%(name)s: %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.INFO)

    handler = logging.FileHandler(filename='discord.log', encoding='utf-8',
                                  mode='a')
    handler.setFormatter(logging.Formatter(FORMAT))
    handler.setLevel(logging.INFO)

    logging.getLogger().addHandler(handler)

    logger.info("========NEW SESSION=========")


if __name__ == '__main__':
    set_up_logs()
    client = MyClient()
    info = get_globals()
    if info:
        token = info['props']['token']
        prefix = info['props']['prefix']
        uuids = info['uuids']
        client.run(token)
    else:
        print("Something failed (this is very vague)")
