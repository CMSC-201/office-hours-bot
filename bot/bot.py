import logging

import mongo
import time
import asyncio
import discord
from discord import Message, Guild, Member, User, Intents
# from discord.app_commands import Command, CommandTree

from channels import ChannelAuthority
from command import handle_message, set_default_guild
from globals import get_globals

from command.submit_interface import SubmitDaemon

logger = logging.getLogger('bot_main')


class MyClient(discord.Client):
    def __init__(self, **options):
        intents = Intents.all()
        # you must enable the member intents in the app/bot settings or else this will crash the bot.
        # but you must also set intents.members = True otherwise you cannot get any member data.
        intents.members = True
        intents.typing = True
        intents.presences = True
        intents.guilds = True
        self.event_loop = None
        super().__init__(intents=intents)
        self.channel_authority: ChannelAuthority = None
        self.submit_daemon = SubmitDaemon(self) if options.get('submit_daemon', False) else None

    async def on_ready(self):
        logger.info('Logged on as {0}!'.format(self.user))
        if len(self.guilds) > 1:
            logger.info("Bot cannot manage more than one guild at this time, probably.")
            for guild in self.guilds:
                logger.info(f"{guild.name} has id {guild.id}")
            logger.info("Checking for default server in database...")
            approved_guilds = mongo.db['approved-guilds']
            for guild in self.guilds:
                if guild.id != approved_guilds.find_one({'guild-id': guild.id}):
                    logger.info(f"Leaving unapproved guild {guild.name} with id {guild.id}")
                    await guild.leave()
        elif len(self.guilds) == 0:
            logger.info('The bot is not a member of any guilds. Exiting...')
            return

        self.event_loop = asyncio.get_event_loop()

        set_default_guild(self.guilds[0])
        logger.info("Bot started.  Waiting for messages.")
        if self.submit_daemon and not self.submit_daemon.is_alive():
            self.submit_daemon.event_loop = self.event_loop
            self.submit_daemon.start()

    async def on_message(self, message: Message):
        guild: Guild = message.guild
        if message.guild:
            logger.info('Message ({0.channel.name}):{0.author}: {0.content}'.format(message))
        else:
            logger.info('Message (DirectMsg, {0.channel.recipient}):{0.author}: {0.content}'.format(message))

        # Ignore bot messages
        if message.author == self.user:
            return

        await handle_message(message, self)

    async def on_member_join(self, member: Member):
        """
            We would like to send the users messages, but I've commented this out because there has been a change
            where the bots are being flagged as spam.
        """
        # global_info = get_globals()
        # class_name = global_info['props'].get('class_name', 'CMSC 201')
        # bot_name = global_info['props'].get('bot_name', 'CMSC 201 Bot')
        # await member.send(f'Welcome to Discord Office Hours for {class_name}\n '
        #                  f'I am the {bot_name}.\n  Send me a message with !auth (your key pasted here), and we\'ll authenticate you on the channel.')
        pass

def set_up_logs(bot_prefix):
    FORMAT = '%(asctime)s:%(levelname)s:%(name)s: %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.INFO)

    try:
        handler = logging.FileHandler(filename=f'/etc/log_data/{bot_prefix}.log', encoding='utf-8', mode='a')
    except FileNotFoundError:
        handler = logging.FileHandler(filename=f'discord.log', encoding='utf-8', mode='a')
    handler.setFormatter(logging.Formatter(FORMAT))
    handler.setLevel(logging.INFO)

    logging.getLogger().addHandler(handler)

    logger.info("========NEW SESSION=========")


if __name__ == '__main__':
    info = get_globals()
    set_up_logs(info['props']['prefix'])

    logger.info(str(info['props']))

    if info:
        token = info['props']['token']
        prefix = info['props']['prefix']
        uuids = info['uuids']
        use_submit_daemon = True if 'submit_daemon' in info['props'] and info['props']['submit_daemon'] == 'true' else False
        if use_submit_daemon:
            logger.info('Using Submit Daemon')
        else:
            logger.info('Not Using Submit Daemon')
        client = MyClient(submit_daemon=use_submit_daemon)

        returned = False
        while not returned:
            try:
                client.run(token)
                returned = True
            except Exception as e:
                returned = True
                logger.error(repr(e))
                logger.info('Restarting Bot from Exception Failure...')
                time.sleep(5)
    else:
        logger.error("Something failed (this is very vague)")
