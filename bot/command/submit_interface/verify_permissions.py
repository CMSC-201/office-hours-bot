"""

"""

import re
import socket

from discord import Message, Client, User, TextChannel

import mongo
import command
import globals
import logging
from typing import Optional, Union
import paramiko
from paramiko.ssh_exception import AuthenticationException, SSHException


@command.command_class
class VerifyGLPermissions(command.Command):
    """
        For some reason this command among all the commands won't load...
    """

    __COMMAND_REGEX = r"!submit\s+verify\s+permissions\s+(?P<assign_name>\w+)\s+(?P<student_id>\w+)"
    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'

    __ROSTER_NAME = 'submit_roster.csv'
    __EXTENSIONS_NAME = 'extensions.json'
    __TIMEOUT = 5

    __BASE_SUBMIT_DIR = globals.get_globals()['props']['base_submit_dir']

    permissions = {'student': False, 'ta': False, 'admin': True}

    def connect_ssh(self):
        self.ssh_client = paramiko.client.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh_client.connect('gl.umbc.edu', username=self.submit_admins['username'], password=self.submit_admins['password'], timeout=self.__TIMEOUT)
            logging.info('Logged into ssh on the GL server.')
        except AuthenticationException:
            logging.info('GL server not able to authenticate.')
            self.ssh_client = None
        except socket.gaierror:
            self.ssh_client = None

        return self.ssh_client

    @command.Command.authenticate
    @command.Command.require_maintenance
    async def handle(self):
        regex_match = re.match(self.__COMMAND_REGEX, self.message.content)
        if not regex_match:
            return False

        user = regex_match.group('student_id')
        assignment_name = regex_match.group('assign_name')
        path = f"{self.__BASE_SUBMIT_DIR}/{assignment_name}/{user}"
        found = False

        self.submit_admins = mongo.db[self.__SUBMIT_SYSTEM_ADMINS].find_one()
        ssh_client = self.connect_ssh()
        if not ssh_client:
            self.message.channel.send(f'Unable to log into the GL server after a timeout of {self.__TIMEOUT} seconds.')
            return False
        _, std_out, _ = ssh_client.exec_command(f"fs la {path} {user}")
        response_lines = std_out.readlines()
        for line in response_lines:
            split_line = line.strip().split()
            if len(split_line) == 2 and split_line[0] == user:
                found = True
                if 'a' in split_line[1]:
                    await self.message.channel.send(f'{user} has admin access for {assignment_name}')
                elif 'w' in split_line[1]:
                    await self.message.channel.send(f'{user} has write access for {assignment_name}')
                elif 'r' in split_line[1]:
                    await self.message.channel.send(f'{user} has read only access for {assignment_name}')

        if not found:
            await self.message.channel.send(f'{user} was not found in the access permissions for {assignment_name}')


    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        __COMMAND_REGEX = r"!submit\s+verify\s+permissions\s+(?P<assign_name>\w+)\s+(?P<student_id>\w+)"
        if re.match(__COMMAND_REGEX, message.content):
            return True

        return False
