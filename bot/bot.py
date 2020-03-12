import json
import logging
import os

import discord

logger = logging.getLogger('bot_main')


class MyClient(discord.Client):
    async def on_ready(self):
        logger.info('Logged on as {0}!'.format(self.user))

    async def on_message(self, message):
        if message.content.startswith('hashbot'):
            await message.channel.send('https://gph.is/28LBdcE')
        logger.info('Message from {0.author}: {0.content}'.format(message))


def get_props():
    global token
    if os.path.exists('../prop.json'):
        with open('../prop.json', 'r') as f:

            return json.load(f)
    else:
        return {
            "token": os.environ.get("BOT_TOKEN"),
            "mongodb-address": os.environ.get("MONGODB_ADDRESS"),
        }


def set_up_logs():
    FORMAT = '%(asctime)s:%(levelname)s:%(name)s: %(message)s'
    logging.basicConfig(format=FORMAT)
    handler = logging.FileHandler(filename='discord.log', encoding='utf-8',
                                  mode='a')
    handler.setFormatter(
        logging.Formatter(FORMAT))
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.info("========NEW SESSION=========")


if __name__ == '__main__':
    set_up_logs()
    client = MyClient()
    token = get_props()['token']
    client.run(token)

