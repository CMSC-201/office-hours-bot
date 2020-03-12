import json
import os

import discord


class MyClient(discord.Client):
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))

    async def on_message(self, message):
        if message.content.startswith('hashbot'):
            await message.channel.send('https://gph.is/28LBdcE')
        print('Message from {0.author}: {0.content}'.format(message))


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


if __name__ == '__main__':
    client = MyClient()
    token = get_props()['token']
    client.run(token)
