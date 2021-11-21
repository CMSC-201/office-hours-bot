import asyncio
import re
import globals
from command import Command, command_class
from discord import Message, Client, Embed
import logging
import mongo
import paramiko
from datetime import datetime
from typing import Optional
from threading import Thread, Lock
from discord import Color
from submit_interface.gl_server_monitor import GLSSHClient


class GLCheckThread(Thread, GLSSHClient):
    __BASE_SUBMIT_DIR = globals.get_globals()['props']['base_submit_dir']
    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'

    def __init__(self, server_number: int, maintenance_channel, main_event_loop, gl_lock: Lock, gl_embed: Embed, embed_message: Message):
        super().__init__(daemon=True)
        self.server_number: int = server_number
        self.maintenance_channel = maintenance_channel
        self.main_event_loop = main_event_loop
        self.ssh_client: Optional[paramiko.client.SSHClient] = None
        self.submit_admins = mongo.db[self.__SUBMIT_SYSTEM_ADMINS]
        self.login_info = self.submit_admins.find_one()
        self.gl_lock: Lock = gl_lock
        self.gl_embed: Embed = gl_embed
        self.embed_message = embed_message

    def run(self):
        self.connect_ssh(self.server_number)
        if self.ssh_client:
            self.ssh_client.exec_command(f'ls {self.__BASE_SUBMIT_DIR}')
            self.gl_embed.set_field_at(self.server_number - 1, name=f'Linux {self.server_number}', value='\u2705 Online')
            logging.info(f"GL Server Check: {self.server_number} is online as of {datetime.now()}")
            asyncio.run_coroutine_threadsafe(self.embed_message.edit(embed=self.gl_embed), self.main_event_loop)
        else:
            self.gl_embed.set_field_at(self.server_number - 1, name=f'Linux {self.server_number}', value='\u274c Offline')
            logging.info(f"GL Server Check: {self.server_number} is offline as of {datetime.now()}")
            asyncio.run_coroutine_threadsafe(self.embed_message.edit(embed=self.gl_embed), self.main_event_loop)


@command_class
class CheckGLServers(Command):

    __COMMAND_REGEX = r"!submit\s+check\s+servers"
    permissions = {'student': False, 'ta': False, 'admin': True}
    check_gl_lock = Lock()

    @Command.authenticate
    @Command.require_maintenance
    async def handle(self):
        gl_embed = Embed(title='GL System Test', color=Color.dark_green())
        for i in range(1, 6 + 1):
            gl_embed.insert_field_at(i - 1, name=f'Linux {i}', value='pending...')
        embed_message = await self.message.channel.send(embed=gl_embed)
        for server_number in [1, 2, 3, 4, 5, 6]:
            GLCheckThread(server_number, self.message.channel, asyncio.get_event_loop(), self.check_gl_lock, gl_embed, embed_message).start()

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if re.match(r"!submit\s+check\s+servers", message.content):
            return True
        return False
