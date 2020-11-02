from discord import Message, Client

import command


@command.command_class
class Bark(command.Command):
    async def handle(self):
        await self.message.channel.send("Ruff!")

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return message.content.startswith("!bark")

@command.command_class
class HelloThere(command.Command):
    async def handle(self):
        await self.message.channel.send('https://media1.tenor.com/images/2eada1bbeb4ed4182079cf00070324a2/tenor.gif?itemid=13903117')

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return message.content.startswith("!hello there")
