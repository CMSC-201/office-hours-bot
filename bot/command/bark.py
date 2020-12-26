from discord import Message, Client

import command


@command.command_class
class Bark(command.Command):
    async def handle(self):
        await self.message.channel.send("Ruff!")

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return message.content.startswith("!bark")

    @classmethod
    def get_help(self):
        return 'Bark: This command will elicit a test response from the bot. \n\t!bark'


@command.command_class
class HelloThere(command.Command):
    async def handle(self):
        await self.message.channel.send('https://media1.tenor.com/images/2eada1bbeb4ed4182079cf00070324a2/tenor.gif?itemid=13903117')

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return message.content.startswith("!hello there")

    @classmethod
    def get_help(self):
        return 'HelloThere: This command will display Obi Wan Kenobi.\n\t!hello there'


@command.command_class
class Squawk(command.Command):
    async def handle(self, new_message=None):
        if new_message:
            if new_message.content.strip().lower() in ['y', 'yes', '!yes']:
                await self.message.channel.send("Squawk!\nDo you want to squawk again? (y/n)")
                return True
            else:
                await self.message.channel.send('You have elected to stop squawking.')
                return False
        else:
            await self.message.channel.send("Squawk!\nDo you want to squawk again? (y/n)")
            return True

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return message.content.startswith("!squawk")

    @classmethod
    def get_help(self):
        return 'This command will elicit a repetition test response from the bot. \n\t!squawk'
