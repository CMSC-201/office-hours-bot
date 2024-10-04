import re
import os
import logging
from discord import Message, Client, User

from paramiko.client import SSHClient
from paramiko import SFTPClient

from socket import timeout

import command
import globals
import mongo
import json
import asyncio
from threading import Thread
from datetime import datetime
from channels import ChannelAuthority


logger = logging.getLogger('bot_main')


@command.command_class
class SubmitResetSSH(command.Command):
    __COMMAND_REGEX = r"!submit\s+reset\s+ssh"

    permissions = {'student': False, 'ta': False, 'admin': True}

    @command.Command.authenticate
    @command.Command.require_maintenance
    async def handle(self):
        if self.client.submit_daemon.ssh_client:
            self.client.submit_daemon.ssh_client.close()
            self.client.submit_daemon.ssh_client = None
        await self.message.channel.send("SSH Reset, Try Again")

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        __COMMAND_REGEX = r"!submit\s+reset\s+ssh"
        if re.match(__COMMAND_REGEX, message.content):
            return True
        return False
