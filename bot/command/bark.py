from discord import Message, Client

import command
import channels


@command.command_class
class Bark(command.Command):
    permissions = {'all': True, 'student': True, 'ta': True, 'admin': True}

    @command.Command.authenticate
    async def handle(self):
        await self.message.channel.send("Ruff!")

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return message.content.startswith("!bark")

    @classmethod
    def get_help(cls):
        return 'Bark: This command will elicit a test response from the bot. \n\t!bark'


@command.command_class
class HelloThere(command.Command):
    permissions = {'student': True, 'ta': True, 'admin': True}

    async def handle(self):
        await self.message.channel.send('https://media1.tenor.com/images/2eada1bbeb4ed4182079cf00070324a2/tenor.gif?itemid=13903117')

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return message.content.startswith("!hello there")

    @staticmethod
    async def is_invoked_by_direct_message(message: Message, client: Client):
        return message.content.startswith("!hello there")

    @classmethod
    def get_help(cls):
        return 'HelloThere: This command will display Obi Wan Kenobi.\n\t!hello there'


@command.command_class
class Squawk(command.Command):
    permissions = {'student': True, 'ta': True, 'admin': True}

    @command.Command.authenticate
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
    def get_help(cls):
        return 'This command will elicit a repetition test response from the bot. \n\t!squawk'


@command.command_class
class MaintenancePing(command.Command):
    permissions = {'student': False, 'ta': False, 'admin': True}

    @command.Command.authenticate
    async def handle(self, new_message=None):
        mc = channels.ChannelAuthority(self.guild).get_maintenance_channel()
        await mc.send('You have pinged the maintenance channel. ')

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return message.content.startswith("!maintenance ping")

    @classmethod
    def get_help(self):
        return 'This command will elicit a test response from the bot on the maintenance channel. \n\t!maintenance ping'
