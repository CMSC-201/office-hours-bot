import logging
from datetime import datetime

from discord import Message, Client, File

import mongo
import command
from globals import get_globals
from queues import QueueAuthority
from roles import RoleAuthority

logger = logging.getLogger(__name__)


@command.command_class
class WhatTimeIsIt(command.Command):

    async def handle(self):
        current_time = datetime.now()
        self.message.channel.send(current_time.strftime("The time is now %H:%M:%S on %m-%d-%y"))

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!what time is it"):
            return True

        return False