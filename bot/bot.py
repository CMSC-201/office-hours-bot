import logging

import time
import discord
from discord import Message, Guild, Member, User, Intents

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
        super().__init__(intents=intents)
        self.channel_authority: ChannelAuthority = None
        self.submit_daemon = SubmitDaemon(self) if options.get('submit_daemon', False) else None

    async def on_ready(self):
        logger.info('Logged on as {0}!'.format(self.user))
        if len(self.guilds) > 1:
            raise ValueError("Bot cannot manage more than one guild at this time.")

        set_default_guild(self.guilds[0])
        logger.info("Bot started.  Waiting for messages.")
        if self.submit_daemon and not self.submit_daemon.is_alive():
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
        global_info = get_globals()
        class_name = global_info['props'].get('class_name', 'CMSC 201')
        bot_name = global_info['props'].get('bot_name', 'CMSC 201 Bot')
        await member.send('Welcome to Discord Office Hours for {}}\n '
                          'I am the {}}.\n  Send me a message with !auth (your key pasted here), and we\'ll authenticate you on the channel.'.format(class_name, bot_name))


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
    info = get_globals()

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
