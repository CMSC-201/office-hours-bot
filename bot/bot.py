import logging

import discord
from discord import Message, Guild

from channels import ChannelAuthority
from command import handle_message
from globals import get_globals

logger = logging.getLogger('bot_main')


class MyClient(discord.Client):
    def __init__(self, **options):
        super().__init__(**options)
        self.channel_authority: ChannelAuthority = None

    async def on_ready(self):
        logger.info('Logged on as {0}!'.format(self.user))
        if len(self.guilds) > 1:
            raise ValueError("Bot cannot manage more than one guild at this time.")

        logger.info("Bot started.  Waiting for messages.")

    async def on_message(self, message: Message):
        guild: Guild = message.guild
        logger.info('Message from {0.author}: {0.content}'.format(message))

        # Ignore bot messages
        if message.author == self.user:
            return

        await handle_message(message, self)

        # ca: ChannelAuthority = ChannelAuthority(message.guild)
        # ra: RoleAuthority = RoleAuthority(message.guild)
        # if ca.is_cleared_channel(message.channel) and not ra.ta_or_higher(message.author):
        #     await message.delete()


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
