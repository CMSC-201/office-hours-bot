import logging

from discord import Message, Guild, Client, Member
from discord.errors import Forbidden

logger = logging.getLogger(__name__)


def name(member: Member):
    return member.nick if member.nick else member.display_name


def is_bot_mentioned(message: Message, client: Client) -> bool:
    users_mentioned_in_role = []
    for role in message.role_mentions:
        users_mentioned_in_role.extend(role.members)

    if client.user in message.mentions or client.user in users_mentioned_in_role:
        return True

    return False


supported_commands = []
the_guild = None


def command_class(cls):
    supported_commands.append(cls)


def set_default_guild(g):
    """
        Necessary in order to ensure that direct messages know the guild (server) on which they're going to operate.

        As long as the_guild in handle_message is defined correctly, this function need not exist.
    :param g: the default guild
    :return: None
    """
    global the_guild
    the_guild = g


async def handle_message(message: Message, client: Client):
    """
    :param message:
    :param client:
    :return:
    """

    if not message.guild:
        for cmd_class in supported_commands:
            if await cmd_class.is_invoked_by_direct_message(message, client):
                command = cmd_class(message, client, the_guild)
                await command.handle()
                break
    else:
        for cmd_class in supported_commands:
            if await cmd_class.is_invoked_by_message(message, client):
                command = cmd_class(message, client)
                await command.handle()
                break


class Command:
    def __init__(self, message: Message = None, client: Client = None, guild: Guild = None):
        if not message:
            raise ValueError("You must issue a command with a message or guild")
        self.message: Message = message
        self.guild: Guild = guild if guild else message.guild
        self.client = client

    async def handle(self):
        raise AttributeError("Must be overwritten by command class")

    async def safe_send(self, destination, message: str, **kwargs) -> bool:
        """
            Generally, messages will send and not be rejected.  However, even if some users haven't disabled DMs from the server, they may
                occasionally generate a discord.errors.Forbidden exception, which will cause further code not to execute.
                In order to be able to ensure that code will execute even if a DM doesn't send properly, this method should be used.
        :param destination: should be a TextChannel or Author/User object (something with a send method)
        :param message: the string message to send
        :param kwargs:
            'backup': an alternative author/channel to send the message if the first is Forbidden
        :return: True if message sent, otherwise False
        """
        try:
            await destination.send(message)
            return True
        except Forbidden as f:
            print(f)
            if kwargs.get('backup', None):
                return await self.safe_send(kwargs['backup'], message)
            return False
        except Exception as e:
            print(e)
            return False

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return False

    @staticmethod
    async def is_invoked_by_direct_message(message: Message, client: Client):
        return False

    def get_help(self):
        return '{}\tThis command has no help text.'.format(self.__class__.__name__)


## DO NOT MOVE THIS CODE
# The following imports all the modules in command so that they can be added to the
# command interpreter.
import pkgutil

__all__ = []
for loader, module_name, is_pkg in pkgutil.walk_packages(__path__):
    __all__.append(module_name)
    _module = loader.find_module(module_name).load_module(module_name)
    globals()[module_name] = _module
