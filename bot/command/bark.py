from discord import Message, Client

import command


@command.command_class
class Bark(command.Command):
    async def handle(self):
        await self.message.channel.send("Ruff!")

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return message.content.startswith("!bark")
