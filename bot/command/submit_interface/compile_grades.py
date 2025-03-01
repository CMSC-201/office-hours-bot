__DOCSTRING__ = """

"""

import re
import json
import os
import logging
import csv
import asyncio
from typing import Optional
from datetime import datetime, timedelta
from discord import Message, Client
from channels import ChannelAuthority

import paramiko
from paramiko.ssh_exception import AuthenticationException, SSHException
from threading import Thread
import command
import mongo
import globals


class CompileGradesThread(Thread):
    """
        This will call the finalize_grades.py script in the admin directory and then send the csv of compiled grades as an attachment to a message in the maintenance
        channel.
    """
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'
    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'

    __BASE_SUBMIT_DIR = globals.get_globals()['props']['base_submit_dir']
    __FINALIZE_GRADING_SCRIPT = '/admin/finalize_grading.py {} --{} --force'

    def __init__(self, assignment: str, suffix: str, message_event_loop, maintenance_channel):
        """
        :param assignment: a string representing the assignment name
        :param closure_datetime: the datetime object representing when the extension will close
        :param login_info: admin username and password to log into the GL server.
        :param lock: a mutex to ensure only one extension closes at a time/semaphore to ensure that only a certain number do.
        :param message_event_loop: the event loop from the main thread, used for sending messages
        """
        super().__init__(daemon=True)
        self.assignment = assignment
        self.suffix = suffix
        self.ssh_client: Optional[paramiko.client.SSHClient] = None
        self.login_info = mongo.db[self.__SUBMIT_SYSTEM_ADMINS].find_one()
        self.event_loop = message_event_loop
        self.assignments = mongo.db[self.__SUBMIT_ASSIGNMENTS]
        self.maintenance_channel = maintenance_channel

    def connect_ssh(self, timeout=10):
        """
        Attempt to connect to the GL server via ssh.  Always reset the connection, do not allow ssh to fail silently.
        Requires the self.login_info to be set.
        :return: the ssh_client
        """
        self.ssh_client = paramiko.client.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh_client.connect('gl.umbc.edu', username=self.login_info['username'], password=self.login_info['password'], timeout=timeout)
            logging.info('Logged into ssh on the GL server.')
        except AuthenticationException:
            logging.info('GL server not able to authenticate.')

        return self.ssh_client

    def run(self):
        asyncio.run_coroutine_threadsafe(self.maintenance_channel.send(f'Compiling Grades for {self.assignment} with suffix {self.suffix}'), self.event_loop)
        assignment_name = self.assignment
        logging.info(f'Running compile grade script for assignment {assignment_name}')

        self.ssh_client = self.connect_ssh()
        if not self.ssh_client:
            asyncio.run_coroutine_threadsafe(self.maintenance_channel.send('Unable to SSH into the GL server.'), self.event_loop)
            return

        _, output_stream, error_stream = self.ssh_client.exec_command(
            'python3 ' + self.__BASE_SUBMIT_DIR + self.__FINALIZE_GRADING_SCRIPT.format(assignment_name, self.suffix))
        error_string = error_stream.read().decode('utf-8')
        if error_string:
            asyncio.run_coroutine_threadsafe(self.maintenance_channel.send('\tCompiling the Grades for {} with {} Caused an Error '.format(assignment_name, self.suffix) +
                                                                           '\n' + error_string), self.event_loop)
        else:
            asyncio.run_coroutine_threadsafe(self.maintenance_channel.send('\tCompiling the Grades for {} with {} Completed Successfully. '.format(assignment_name, self.suffix)),
                                             self.event_loop)

        if not os.path.isdir('csv_dump'):
            os.mkdir('csv_dump')

        # get the grades CSV file
        ftp_client = self.ssh_client.open_sftp()
        file_source = os.path.join(self.__BASE_SUBMIT_DIR, 'admin', 'grades', f'{assignment_name.upper()}',
                                   f'{assignment_name}_grades.csv')
        file_destination = os.path.join('csv_dump', f'{assignment_name}_grades.csv')

        asyncio.run_coroutine_threadsafe(self.maintenance_channel.send(f'Looking for grades file at {file_source} saving to {file_destination} '), self.event_loop)
        ftp_client.get(file_source, file_destination)
        ftp_client.close()

        asyncio.run_coroutine_threadsafe(self.maintenance_channel.send(f'FTP Operation Completed. '), self.event_loop)
        if os.path.isfile(file_destination):
            asyncio.run_coroutine_threadsafe(self.maintenance_channel.send(f'The grades for {assignment_name} with {self.suffix.upper()} are here: ', file=file_destination),
                                             self.event_loop)
        else:
            asyncio.run_coroutine_threadsafe(self.maintenance_channel.send(f'The grades for {assignment_name} with {self.suffix.upper()} file was not found: '), self.event_loop)


@command.command_class
class CompileGrades(command.Command):
    __COMMAND_REGEX = r"!submit\s+compile\s+grades\s+(?P<assign_name>(\w+|[_])) (?P<suffix>\w+)"
    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'

    __ROSTER_NAME = 'submit_roster.csv'
    __EXTENSIONS_NAME = 'extensions.json'

    __BASE_SUBMIT_DIR = globals.get_globals()['props']['base_submit_dir']
    __ADMIN__CLOSE_ASSIGNMENT = '/admin/close_assignment.py {} {} {}'
    __CLOSE_STUDENT_EXTENSION = '/admin/close_extension.py {} student={}'
    __CLOSE_SECTION_EXTENSION = '/admin/close_extension.py {} section={} {}'

    permissions = {'student': False, 'ta': False, 'admin': True}

    @command.Command.authenticate
    @command.Command.require_maintenance
    async def handle(self):
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        the_match = re.match(self.__COMMAND_REGEX, self.message.content)
        if not the_match:
            await self.message.channel.send('Assignment Compile Grades Error: Does not match template.  !submit compile grades <assignment name>')
        assignment_name = the_match.group('assign_name')
        suffix = the_match.group('suffix')
        CompileGradesThread(assignment_name, suffix, asyncio.get_event_loop(), ca.get_maintenance_channel()).start()

    @classmethod
    async def is_invoked_by_message(cls, message: Message, client: Client):
        if re.match(cls.__COMMAND_REGEX, message.content):
            return True
        return False
