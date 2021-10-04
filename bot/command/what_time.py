"""
what_time.py

    Command: !what time is it

    Responds with the server/docker container time.

    Roles:      All (authed)
    Channels:   All, DM
"""
__author__ = 'EJH'

import logging
import command

from datetime import datetime
from discord import Message, Client


logger = logging.getLogger(__name__)


@command.command_class
class WhatTimeIsIt(command.Command):
    """
        This command is intended to tell us what time it is on the server which the bot is running.

        If it's running in a docker component this is useful to know as well.

        The command is run by typing: !what time is it
    """

    permissions = {'student': True, 'ta': True, 'admin': True}

    @command.Command.authenticate
    async def handle(self):
        current_time = datetime.now()
        await self.message.channel.send(current_time.strftime("The time is now %H:%M:%S on %m-%d-%y"))

    @staticmethod
    async def is_invoked_by_direct_message(message: Message, client: Client):
        if message.content.startswith("!what time is it"):
            return True

        return False

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!what time is it"):
            return True

        return False

    @classmethod
    def get_help(cls):
        help_string = """
            !what time is it
                This command gives the time on the server (or the docker component) where this bot is running.
        """
        return help_string
