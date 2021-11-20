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

import paramiko
from paramiko.ssh_exception import AuthenticationException, SSHException
from threading import Thread
import command
import mongo
import globals


class CloseAssignmentThread(Thread):
    """

    """
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'
    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'

    __USERNAME = 'UMBC-Name-Id'
    __SECTION = 'Section'
    __DISCORD_ID = 'discord'
    __FIRST_NAME = 'First-Name'
    __LAST_NAME = 'Last-Name'
    __UID_FIELD = 'UMBC-Name-Id'

    __BASE_SUBMIT_DIR = globals.get_globals()['props']['base_submit_dir']
    __ADMIN__CLOSE_ASSIGNMENT = '/admin/close_assignment.py {} {} {}'
    __CLOSE_STUDENT_EXTENSION = '/admin/close_extension.py {} student={}'
    __CLOSE_SECTION_EXTENSION = '/admin/close_extension.py {} section={} {}'

    __ROSTER_NAME = 'submit_roster.csv'
    __EXTENSIONS_NAME = 'extensions.json'

    def __init__(self, assignment: str, closure_datetime: datetime, lock, message_event_loop, status_report, maintenance_channel):
        """
        :param assignment: a string representing the assignment name
        :param closure_datetime: the datetime object representing when the extension will close
        :param login_info: admin username and password to log into the GL server.
        :param lock: a mutex to ensure only one extension closes at a time/semaphore to ensure that only a certain number do.
        :param message_event_loop: the event loop from the main thread, used for sending messages
        """
        super().__init__(daemon=True)
        self.assignment = assignment
        self.closure_datetime = closure_datetime
        self.ssh_client: Optional[paramiko.client.SSHClient] = None
        self.login_info = mongo.db[self.__SUBMIT_SYSTEM_ADMINS].find_one()
        self.lock = lock
        self.event_loop = message_event_loop
        self.status_report = status_report
        self.assignments = mongo.db[self.__SUBMIT_ASSIGNMENTS]
        self.maintenance_channel = maintenance_channel

    def connect_ssh(self, timeout=10):
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
                self.ssh_client.connect('gl.umbc.edu', username=self.login_info['username'], password=self.login_info['password'], timeout=timeout)
                logging.info('Logged into ssh on the GL server.')
            except AuthenticationException:
                logging.info('GL server not able to authenticate.')

        return self.ssh_client

    def write_roster(self):
        students_group = mongo.db[self.__STUDENTS_GROUP]
        ta_group = mongo.db[self.__TA_GROUP]
        admin_group = mongo.db[self.__ADMIN_GROUP]

        if not os.path.exists('csv_dump'):
            os.makedirs('csv_dump')

        with open(os.path.join('csv_dump', self.__ROSTER_NAME), 'w', newline='') as csv_file:
            roster = csv.writer(csv_file)
            roster_list = [[student[self.__USERNAME], student[self.__SECTION]] for student in students_group.find()]
            roster_list.extend([[ta[self.__USERNAME], ta[self.__SECTION]] for ta in ta_group.find()])
            roster_list.extend([[admin[self.__USERNAME], 0] for admin in admin_group.find()])
            roster.writerows(roster_list)

    def write_extension_file(self):
        extensions_json = {}
        with open(os.path.join('csv_dump', self.__EXTENSIONS_NAME), 'w') as json_extensions_file:
            for assignment in self.assignments.find():
                extensions_json[assignment['name']] = {'section-extensions': {},
                                                       'student-extensions': {}}

                for student in assignment['student-extensions']:
                    due_date = assignment['student-extensions'][student]['due-date'].strftime('%Y.%m.%d.%H.%M.%S')
                    if assignment['student-extensions'][student]['due-date'] > datetime.now():
                        extensions_json[assignment['name']]['student-extensions'][student] = due_date
                for section in assignment['section-extensions']:
                    due_date = assignment['section-extensions'][section]['due-date'].strftime('%Y.%m.%d.%H.%M.%S')
                    extensions_json[assignment['name']]['section-extensions'][section] = due_date

            json_extensions_file.write(json.dumps(extensions_json, indent='\t'))

    def run(self):
        assignment_name = self.assignment
        assignment = self.assignments.find_one({'name': assignment_name})
        if not assignment:
            asyncio.run_coroutine_threadsafe(self.maintenance_channel.send('Assignment {} was not found. '.format(assignment_name)), self.event_loop)
            logging.info('Assignment {} was not found. '.format(assignment_name))
            return

        logging.info('Running close assignment script for assignment {}'.format(assignment_name))

        self.write_roster()
        self.write_extension_file()

        self.ssh_client = self.connect_ssh()
        ftp_client = self.ssh_client.open_sftp()
        ftp_client.put(os.path.join('csv_dump', self.__ROSTER_NAME), self.__BASE_SUBMIT_DIR + '/admin/' + self.__ROSTER_NAME)
        ftp_client.put(os.path.join('csv_dump', self.__EXTENSIONS_NAME), self.__BASE_SUBMIT_DIR + '/admin/' + self.__EXTENSIONS_NAME)
        ftp_client.close()
        asyncio.run_coroutine_threadsafe(self.maintenance_channel.send('New roster and extension files written to GL server by FTP. '), self.event_loop)
        roster_path = self.__BASE_SUBMIT_DIR + '/admin/' + self.__ROSTER_NAME
        extensions_path = self.__BASE_SUBMIT_DIR + '/admin/' + self.__EXTENSIONS_NAME
        logging.info('python3 ' + self.__BASE_SUBMIT_DIR + self.__ADMIN__CLOSE_ASSIGNMENT.format(assignment_name, roster_path, extensions_path))
        self.ssh_client.exec_command('python3 ' + self.__BASE_SUBMIT_DIR + self.__ADMIN__CLOSE_ASSIGNMENT.format(assignment_name, roster_path, extensions_path))
        self.status_report['closed'] = True
        asyncio.run_coroutine_threadsafe(self.maintenance_channel.send('Sending ssh command to close assignment {} on the GL server. '.format(assignment_name)), self.event_loop)
        self.assignments.update_one({'name': assignment_name}, {'$set': {'open': False}})
        asyncio.run_coroutine_threadsafe(self.maintenance_channel.send('Updating Database with assignment {} closure. '.format(assignment_name)), self.event_loop)
        self.status_report['sent'] = True


@command.command_class
class CloseAssignment(command.Command):
    __COMMAND_REGEX = r"!submit\s+configure\s+(?P<assign_name>\w+)\s+remove(\s+(?P<admin>--admin=\w+))?"
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
        the_match = re.match(r"!submit\s+close\s+assignment\s+(?P<assign_name>\w+)", self.message.content)
        if not the_match:
            await self.message.channel.send('Close Assignment Error: Does not match template.  !submit close assignment <assignment name>')
        assignment_name = the_match.group('assign_name')
        assignment = self.assignments.find_one({'name': assignment_name})
        if assignment['open']:
            # , assignment: str, closure_datetime: datetime, lock, message_event_loop, status_report, maintenance_channel):
            pass
            # CloseAssignmentThread(assignment_name, None, )
        else:
            pass


    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if re.match(r"!submit\s+close\s+assignment\s+(?P<assign_name>\w+)", message.content):
            return True
        return False
