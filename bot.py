import os

import discord


class MyClient(discord.Client):
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))

    async def on_message(self, message):
        if message.content.startswith('hashbot'):
            await message.channel.send('https://gph.is/28LBdcE')
        print('Message from {0.author}: {0.content}'.format(message))


def get_token():
    global token
    if os.path.exists('token'):
        with open('token', 'r') as f:
            token = f.read()
    else:
        token = os.environ.get("BOT_TOKEN")


if __name__ == '__main__':
    client = MyClient()
    token = get_token()

    client.run(token)
