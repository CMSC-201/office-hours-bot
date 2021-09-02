import logging

import discord
from discord import Message, Guild, Member, User, Intents

from channels import ChannelAuthority
from command import handle_message, set_default_guild
from globals import get_globals

from command.submit_interface import SubmitDaemon

logger = logging.getLogger('bot_main')


class MyClient(discord.Client):
    def __init__(self, **options):
        intents = Intents.default()
        # this will case a crash
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
        if self.submit_daemon:
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
        await member.send('Welcome to Discord Office Hours for CMSC 201, Spring 2021\n '
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
    info = get_globals()

    use_submit_daemon = True if 'submit_daemon' in info['props'] and info['props']['submit_daemon'] == 'true' else False
    client = MyClient(submit_daemon=use_submit_daemon)

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
                returned = True
                print(e)
                print('Restarting Bot from Exception Failure...')

    else:
        print("Something failed (this is very vague)")
