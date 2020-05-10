import logging
import unittest
from os import environ
from unittest import TestCase

import discord
from discord import Message, TextChannel

logger = logging.getLogger('bot_main')


class TestBot(discord.Client):
    def __init__(self, tester=None, **options):
        super().__init__(**options)
        # self.callback = callback
        self.tester = tester

    async def on_ready(self):
        logger.info('Logged on as {0}!'.format(self.user))

        await self.test_bark()

        await self.close()

    async def test_bark(self):
        def callback(message: Message):
            if 'ruff!' in message.content.lower():
                return True

        await self.send_message_to_channel("general", "!bark")

        result = await self.wait_for('message', timeout=60.0, check=callback)
        self.tester.assertTrue(result)

    async def send_message_to_channel(self, channel_name, message):
        channel: TextChannel
        for channel in self.get_all_channels():
            if channel.name == channel_name:
                await channel.send(message)

    async def on_message(self, message: Message):
        if message.author == self:
            return
        #
        # self.callback(message)


class BotTest(TestCase):
    def test_env(self):
        env_vars = [
            'BOT_TOKEN',
            'MONGODB_URI',
            'QUEUE_URL',
            'TEST_BOT_TOKEN',
        ]
        for var in env_vars:
            self.assertTrue(var in environ)

    def test_bark(self):
        token = environ['TEST_BOT_TOKEN']
        print(token)
        test_bot = TestBot(tester=self)
        test_bot.run(token)


if __name__ == '__main__':
    FORMAT = '%(asctime)s:%(levelname)s:%(name)s: %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.INFO)

    handler = logging.FileHandler(filename='discord.log', encoding='utf-8',
                                  mode='a')
    handler.setFormatter(logging.Formatter(FORMAT))
    handler.setLevel(logging.INFO)

    logging.getLogger().addHandler(handler)
    unittest.main()
