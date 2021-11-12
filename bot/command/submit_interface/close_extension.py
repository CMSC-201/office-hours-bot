"""

"""

import time
import re
from datetime import datetime, timedelta
from discord import Message, Client, User, TextChannel

import command
import mongo
import globals
import asyncio
import logging
from threading import Thread
from typing import Optional, Union
import paramiko
from paramiko.ssh_exception import AuthenticationException, SSHException

from channels import ChannelAuthority
from submit_interface.submit_exceptions import AlreadyClosingException


class StudentExtensionClosureThread(Thread):
    """
        Under construction, undergoing testing.

    """
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'

    __USERNAME = 'UMBC-Name-Id'
    __SECTION = 'Section'
    __DISCORD_ID = 'discord'
    __FIRST_NAME = 'First-Name'
    __LAST_NAME = 'Last-Name'
    __UID_FIELD = 'UMBC-Name-Id'

    __BASE_SUBMIT_DIR = globals.get_globals()['props']['base_submit_dir']
    __CLOSE_STUDENT_EXTENSION = '/admin/close_extension.py {} student={}'

    __ROSTER_NAME = 'submit_roster.csv'
    __EXTENSIONS_NAME = 'extensions.json'

    def __init__(self, assignment: str, student: str, closure_datetime: datetime, login_info, lock, message_event_loop, status_report, maintenance_channel):
        """
        :param assignment: a string representing the assignment name
        :param student: the student whose extension is closing
        :param closure_datetime: the datetime object representing when the extension will close
        :param login_info: admin username and password to log into the GL server.
        :param lock: a mutex to ensure only one extension closes at a time/semaphore to ensure that only a certain number do.
        :param message_event_loop: the event loop from the main thread, used for sending messages
        """
        super().__init__(daemon=True)
        self.assignment = assignment
        self.student = student
        self.closure_datetime = closure_datetime
        self.ssh_client: Optional[paramiko.client.SSHClient] = None
        self.login_info = login_info
        self.lock = lock
        self.event_loop = message_event_loop
        self.status_report = status_report
        self.assignments = mongo.db[self.__SUBMIT_ASSIGNMENTS]
        self.maintenance_channel = maintenance_channel

    def connect_ssh(self):
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
                self.ssh_client.connect('gl.umbc.edu', username=self.login_info['username'], password=self.login_info['password'], timeout=10)
                logging.info('Logged into ssh on the GL server.')
            except AuthenticationException:
                logging.info('GL server not able to authenticate.')

        return self.ssh_client

    def threadsafe_send_message(self, channel: Union[User, TextChannel], message: str):
        """
        In order to send discord messages from a non-prime thread you need to use the asyncio library and run the method from the primary event-loop.

        :param channel: channel or user to send the message
        :param message: the message to send
        """
        logging.info(message)
        asyncio.run_coroutine_threadsafe(channel.send(message), self.event_loop)

    def run(self) -> None:
        students_group = mongo.db[self.__STUDENTS_GROUP]
        if self.lock:
            self.lock.acquire()
        try:
            attempt_count = 0
            while not self.connect_ssh() and attempt_count < 5:
                # determine whether to terminate the thread based on number of attempts to log into the ssh server.
                attempt_count += 1
                self.status_report['failed'] = True
                return

            the_assignment = self.assignments.find_one({'name': self.assignment})
            if not the_assignment['student-extensions'][self.student]['open']:
                raise AlreadyClosingException(f'This extension has already been closed: {self.assignment}: {self.student}', self.assignment)

            while datetime.now() < self.closure_datetime:
                time.sleep(1)

            self.threadsafe_send_message(self.maintenance_channel, f'Closing {self.assignment} extension for student {self.student}')
            self.ssh_client.exec_command('python3 ' + self.__BASE_SUBMIT_DIR + self.__CLOSE_STUDENT_EXTENSION.format(self.assignment, self.student))

            the_assignment['student-extensions'][self.student]['open'] = False
            self.assignments.update_one({'name': self.assignment}, {'$set': {f'student-extensions.{self.student}': the_assignment['student-extensions'][self.student]}})

            the_student = students_group.find_one({self.__UID_FIELD: self.student})
            the_student_name = ' '.join([the_student[self.__FIRST_NAME], the_student[self.__LAST_NAME]])
            maintenance_message = f'{the_student_name} ({the_student[self.__UID_FIELD]})\'s extension for assignment {self.assignment} is now closed.'
            message = f'{self.student} ({the_student[self.__UID_FIELD]})\'s extension for assignment {self.assignment} is now closed.  You should recopy the files and begin grading. '
            self.threadsafe_send_message(self.maintenance_channel, maintenance_message)

            # logging.info('Copying {} extension for student {}'.format(assignment['name'], assignment['student']))
            # self.ssh_client.exec_command('python3 ' + self.__BASE_SUBMIT_DIR + self.__COPY_STUDENT_EXTENSION.format(assignment['name'], assignment['student'], ''))

            # maybe stick these into a database to be safe, but for now let's just try to get this new process working
            self.status_report['student-section'] = the_student[self.__SECTION]
            self.status_report['maintenance-message'] = maintenance_message
            self.status_report['ta-message'] = message
            self.status_report['sent'] = False
            self.status_report['closed'] = True

        except AlreadyClosingException as ace:
            logging.info('Preventing Multiple Runs: ' + ace.message)
        finally:
            if self.lock:
                self.lock.release()


@command.command_class
class CloseExtension(command.Command):
    """
       This class allows us to call the
        !submit close extension [assignment name] [student id] or
        !submit close extension [assignment name] [section id] (not currently implemented)

    """
    __COMMAND_REGEX = r"!submit\s+close\s+extension\s+(?P<assign_name>\w+)\s+(?P<student_id>\w+)"
    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'

    __ROSTER_NAME = 'submit_roster.csv'
    __EXTENSIONS_NAME = 'extensions.json'

    __BASE_SUBMIT_DIR = globals.get_globals()['props']['base_submit_dir']
    __CLOSE_STUDENT_EXTENSION = '/admin/close_extension.py {} student={}'
    __CLOSE_SECTION_EXTENSION = '/admin/close_extension.py {} section={} {}'

    permissions = {'student': False, 'ta': False, 'admin': True}

    @command.Command.authenticate
    @command.Command.require_maintenance
    async def handle(self):
        ca: ChannelAuthority = ChannelAuthority(self.guild)

        match = re.match(self.__COMMAND_REGEX, self.message.content)
        assignment = match.group('assign_name')
        student_id = match.group('student_id')

        self.submit_admins = mongo.db[self.__SUBMIT_SYSTEM_ADMINS]
        self.assignments = mongo.db[self.__SUBMIT_ASSIGNMENTS]

        admin = self.submit_admins.find_one()

        the_assignment = self.assignments.find_one({'name': assignment})
        status_report = {'assignment': the_assignment, 'closed': False, 'sent': False, 'thread': None}
        extension_closure_thread = StudentExtensionClosureThread(assignment, student_id, the_assignment['due-date'], admin, None, asyncio.get_event_loop(), status_report, ca.get_maintenance_channel())
        extension_closure_thread.start()

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if re.match(r"!submit\s+close\s+extension\s+(?P<assign_name>\w+)\s+student\s+=\s+(?P<student_id>\w+)", message.content):
            return True
        if re.match(r"!submit\s+close\s+extension\s+(?P<assign_name>\w+)\s+section\s+=\s+(?P<section_id>\d+)", message.content):
            return True

        return False
