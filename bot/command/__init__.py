import logging

from discord import Message, Guild, Client, Member
from discord.errors import Forbidden, NotFound
from roles import RoleAuthority

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
current_commands = []
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

    global current_commands

    for the_message, command in current_commands:
        if message.author == the_message.author:
            current_commands.remove((the_message, command))
            if await command.handle(message):
                current_commands.append((the_message, command))
                return

    if not message.guild:
        for cmd_class in supported_commands:
            if await cmd_class.is_invoked_by_direct_message(message, client):
                command = cmd_class(message, client, the_guild)
                if await command.handle():
                    current_commands.append((message, command))
                return
    else:
        for cmd_class in supported_commands:
            if await cmd_class.is_invoked_by_message(message, client):
                command = cmd_class(message, client)
                if await command.handle():
                    current_commands.append((message, command))
                return


class Command:
    GUILD_MEMBERS = {}
    permissions = {}

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

    async def safe_delete(self, message: Message, delay: int = 0, admonition: str = "") -> bool:
        try:
            await message.delete(delay=delay)
            return True
        except NotFound:
            if admonition:
                await message.channel.send(admonition)
        except Forbidden:
            if admonition:
                await message.channel.send(admonition)
        return False

    async def get_member(self, user_id, force=False):
        """
            This function should reduce the overall inefficiencies caused by the discord API change
            whereby get_member seems to have been deprecated.

            We will save the first instance of each fetch_member api call and then be permitted to
            reuse those member classes when needed.

        :param user_id: the user_id or member_id from a guild
        :param force: if force is set to True, a new fetch_member will be called, regardless of the cache.
            This can be used to update the member object in the cache from the server.
        :return: the member object.
        """
        if user_id in self.GUILD_MEMBERS and not force:
            return self.GUILD_MEMBERS[user_id]
        else:
            member = await self.guild.fetch_member(user_id)
            self.GUILD_MEMBERS[user_id] = member
            return member

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return False

    @staticmethod
    async def is_invoked_by_direct_message(message: Message, client: Client):
        return False

    @classmethod
    def get_help(cls):
        return '{}, this command has no help text.'.format(cls.__name__)

    @staticmethod
    def authenticate(the_method, **keyword_arguments):
        """
            This will read from the WhateverCommand.permissions object to check
            that the author of self.message has the proper permissions to run
            the command, if so the wrapped handle function will be returned.
            Otherwise it will return a function which posts a message informing
            the user that they do not have permission to run the command.

            :param the_method: the method that uses the authentication process
            :param keyword_arguments:
                message: str: if provided, it will be the message displayed to the user upon failure.
            :return: a wrapper of the_method which ensures proper permissions
                before execution.
        """
        async def authentication_wrapper(self, *args, **kwargs):
            ra: RoleAuthority = RoleAuthority(self.guild)
            if ra.has_permission(self.message.author, self.permissions):
                await the_method(self, *args, **kwargs)
            else:
                await self.safe_send(
                    self.message.channel,
                    keyword_arguments.get('message', 'Unable to execute the command, you do not have permission.'))

        return authentication_wrapper

    @staticmethod
    def require_maintenance(the_method, **keyword_args):
        """
        Ensures that the command which owns the called method is running on the maintenance channel.

        :param the_method: the method to be encapsulated.  Must be a member of a Command child class.
        :param keyword_args:
            message: str: if provided, it will be the message displayed to the user upon failure.
        :return: a channel_authentication_wrapper that ensures that we're on the maintenance
            channel.
        """

        async def channel_authentication_wrapper(self, *args, **kwargs):
            from channels import ChannelAuthority
            ca: ChannelAuthority = ChannelAuthority(self.guild)
            if ca.is_maintenance_channel(self.message.channel):
                await the_method(self, *args, **kwargs)
            else:
                await self.safe_send(
                    self.message.channel,
                    keyword_args.get('message', 'This command must be run on the maintenance channel. '))

        return channel_authentication_wrapper




## DO NOT MOVE THIS CODE
# The following imports all the modules in command so that they can be added to the
# command interpreter.
import pkgutil

__all__ = []
for loader, module_name, is_pkg in pkgutil.walk_packages(__path__):
    __all__.append(module_name)
    _module = loader.find_module(module_name).load_module(module_name)
    globals()[module_name] = _module
