import asyncio
import re
import globals
from command import Command, command_class
from discord import Message, Client, Embed, TextChannel
import logging
import time
import mongo
import paramiko
from datetime import datetime
from typing import Optional, List
from paramiko.ssh_exception import AuthenticationException, SSHException
from threading import Thread, Lock
import socket
from discord import Color


class GLSSHClient:
    # ensure that when the constructor is not run, this is still set to None
    ssh_client: Optional[paramiko.client.SSHClient] = None

    def __init__(self):
        self.ssh_client: Optional[paramiko.client.SSHClient] = None
        self.login_info = {'username': '', 'password': ''}

    def connect_ssh(self, server_number=0, timeout=10):
        """
        Attempt to connect to the GL server via ssh.

        Requires the self.login_info to be set.

        :return: the ssh_client
        """
        if self.ssh_client and (not self.ssh_client.get_transport() or not self.ssh_client.get_transport().is_active()):
            self.ssh_client = None

        if not self.ssh_client:
            self.ssh_client = paramiko.client.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                if not server_number:
                    self.ssh_client.connect(f'linuxserver1.cs.umbc.edu', username=self.login_info['username'], password=self.login_info['password'], timeout=timeout)
                else:
                    self.ssh_client.connect(f'linuxserver{server_number}.cs.umbc.edu', username=self.login_info['username'], password=self.login_info['password'], timeout=timeout)
                logging.info('Logged into ssh on the GL server.')
            except socket.timeout:
                self.ssh_client = None
            except socket.gaierror:
                self.ssh_client = None
            except TimeoutError:
                self.ssh_client = None
            except AuthenticationException:
                logging.info('GL server not able to authenticate.')
                self.ssh_client = None

        return self.ssh_client


class GLMonitorCheck(Thread, GLSSHClient):
    __BASE_SUBMIT_DIR = globals.get_globals()['props']['base_submit_dir']
    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'
    __SUCCESS_SLEEP_PERIOD = 300  # five minutes
    __FAILURE_SLEEP_PERIOD = 300  # just 30 seconds, then retry
    __TIMEOUT = 25  # since we have a failure sleep period of 30 seconds, allow 25 seconds to attempt connection then sleep five seconds

    def __init__(self, server_number: int, display_channel: TextChannel, main_event_loop: asyncio.AbstractEventLoop, gl_lock: Lock):
        super().__init__(daemon=True)
        self.server_number: int = server_number
        self.display_channel: TextChannel = display_channel
        self.main_event_loop: asyncio.AbstractEventLoop = main_event_loop
        self.ssh_client: Optional[paramiko.client.SSHClient] = None
        self.submit_admins = mongo.db[self.__SUBMIT_SYSTEM_ADMINS]
        self.login_info = self.submit_admins.find_one()
        self.gl_lock = gl_lock
        self.gl_embed: Optional[Embed] = None
        self.embed_message: Optional[Message] = None
        self.terminate_signal: bool = False

    def set_message_and_embed(self, message: Message, embed: Embed):
        self.embed_message = message
        self.gl_embed = embed

    def run(self):
        online = False
        while not self.terminate_signal:

            if not online:
                self.gl_embed.set_field_at(self.server_number - 1, name=f'Linux {self.server_number}', value='\u274c Pending...')
                asyncio.run_coroutine_threadsafe(self.embed_message.edit(embed=self.gl_embed), self.main_event_loop)

            self.connect_ssh(self.server_number, self.__TIMEOUT)
            if self.ssh_client:
                self.ssh_client.exec_command(f'ls {self.__BASE_SUBMIT_DIR}')
                online = True
                self.gl_embed.set_field_at(self.server_number - 1, name=f'Linux {self.server_number}', value='\u2705 Online')
                logging.info(f"GL Server Check: {self.server_number} is online as of {datetime.now()}")
                asyncio.run_coroutine_threadsafe(self.embed_message.edit(embed=self.gl_embed), self.main_event_loop)
                time.sleep(self.__SUCCESS_SLEEP_PERIOD)
            else:
                self.gl_embed.set_field_at(self.server_number - 1, name=f'Linux {self.server_number}', value='\u274c Offline')
                logging.info(f"GL Server Check: {self.server_number} is offline as of {datetime.now()}")
                online = False
                asyncio.run_coroutine_threadsafe(self.embed_message.edit(embed=self.gl_embed), self.main_event_loop)
                time.sleep(self.__FAILURE_SLEEP_PERIOD)


class GLMonitorMaster(Thread):
    gl_monitor_lock = Lock()
    gl_monitor_message = None
    gl_monitor_embed = None
    __RECHECK_DELAY = 300

    def __init__(self, server_numbers: List[int], discord_client, display_channel: TextChannel, main_event_loop: asyncio.AbstractEventLoop) -> None:
        super().__init__(daemon=True)
        self.server_numbers = list(server_numbers)
        self.discord_client = discord_client
        self.display_channel = display_channel
        self.main_event_loop = main_event_loop
        self.ssh_client: Optional[paramiko.client.SSHClient] = None
        self.check_threads = {server_number: GLMonitorCheck(server_number, self.display_channel, self.main_event_loop, self.gl_monitor_lock)
                              for server_number in server_numbers}

    def asyncio_send_message(self, channel: TextChannel, message: str, embed: Embed):
        """
            This method should simply send the message or embed to the channel, but since it's using asyncio, it's better to abstract this away.
        """
        return asyncio.run_coroutine_threadsafe(channel.send(message, embed=embed), self.main_event_loop).result()

    def run(self) -> None:
        self.gl_monitor_embed = Embed(title='GL System Monitor', color=Color.dark_green())
        for i in self.server_numbers:
            self.gl_monitor_embed.insert_field_at(i - 1, name=f'Linux {i}', value='pending...')
        self.gl_monitor_message = self.asyncio_send_message(self.display_channel, "", self.gl_monitor_embed)

        for check_thread_name in self.check_threads:
            self.check_threads[check_thread_name].set_message_and_embed(self.gl_monitor_message, self.gl_monitor_embed)
            self.check_threads[check_thread_name].start()


@command_class
class MonitorGLServers(Command):
    __COMMAND_REGEX = r"!submit\s+monitor\s+servers"
    permissions = {'student': False, 'ta': False, 'admin': True}
    monitor_master_thread = Optional[GLMonitorMaster]

    @Command.authenticate
    async def handle(self):
        if not re.match(self.__COMMAND_REGEX, self.message.content):
            return False

        self.monitor_master_thread: GLMonitorMaster = GLMonitorMaster([1, 2, 3, 4, 5, 6], self.client, self.message.channel, asyncio.get_event_loop())
        if not self.monitor_master_thread or not self.monitor_master_thread.is_alive():
            self.monitor_master_thread = GLMonitorMaster([1, 2, 3, 4, 5, 6], self.client, self.message.channel, asyncio.get_event_loop())
            self.monitor_master_thread.start()

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if re.match(r"!submit\s+monitor\s+servers", message.content):
            return True
        return False
