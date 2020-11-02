import logging

import discord
from discord import Message, Guild, Member, User

from channels import ChannelAuthority
from command import handle_message, set_default_guild
from globals import get_globals

from command.submit_interface import SubmitDaemon

logger = logging.getLogger('bot_main')


class MyClient(discord.Client):
    def __init__(self, **options):
        super().__init__(**options)
        self.channel_authority: ChannelAuthority = None
        self.submit_daemon = SubmitDaemon(self)

    async def on_ready(self):
        logger.info('Logged on as {0}!'.format(self.user))
        if len(self.guilds) > 1:
            raise ValueError("Bot cannot manage more than one guild at this time.")

        set_default_guild(self.guilds[0])
        logger.info("Bot started.  Waiting for messages.")
        self.submit_daemon.start()

    async def on_message(self, message: Message):
        guild: Guild = message.guild

        if message.guild:
            logger.info('Message ({0.channel.name}):{0.author}: {0.content}'.format(message))
        else:
            logger.info('Message (DirectMsg):{0.author}: {0.content}'.format(message))

        # Ignore bot messages
        if message.author == self.user:
            return

        await handle_message(message, self)

    async def on_member_join(self, member: Member):
        # update this message with your own course and message
        await member.send('Welcome to Discord Office Hours for CMSC 201, Fall 2020\n '
                          'I am the 201Bot.\n  Send me a message with !auth (your key pasted here), and we\'ll authenticate you on the channel.')


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
        returned = False
        while not returned:
            try:
                client.run(token)
                returned = True
            except Exception as e:
                print(e)
                print('Restarting Bot from Exception Failure...')

    else:
        print("Something failed (this is very vague)")
