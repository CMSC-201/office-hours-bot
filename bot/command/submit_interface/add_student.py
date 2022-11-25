__DOCSTRING__ = """

"""

import re
import globals
from datetime import datetime, timedelta
from discord import Message, Client


import command
import mongo
import asyncio
from paramiko.client import SSHClient

from threading import Thread


class AddStudentAssignmentsThread(Thread):
    __BASE_SUBMIT_DIR = globals.get_globals()['props']['base_submit_dir']
    __ROSTER_NAME = 'submit_roster.csv'
    __EXTENSIONS_NAME = 'extensions.json'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'

    def __init__(self, client, student_id, assignments, maintenance_channel=None, main_loop=None):
        super().__init__(daemon=True)
        self.client = client
        self.student_id = student_id
        self.maintenance_channel = maintenance_channel
        self.main_loop = main_loop
        self.assignments = assignments

    def run(self):
        ssh_client: SSHClient = self.client.submit_daemon.connect_ssh()
        assignments_with_read = []
        assignments_with_write = []
        try:
            for assignment_name in self.assignments:
                _, output, errors = ssh_client.exec_command(f'mkdir {self.__BASE_SUBMIT_DIR}/{assignment_name}/{self.student_id}')
                if self.assignments[assignment_name]['due-date'] < datetime.now():
                    _, output, errors = ssh_client.exec_command(f'fs sa {self.__BASE_SUBMIT_DIR}/{assignment_name}/{self.student_id} {self.student_id} read')
                    assignments_with_read.append(assignment_name)
                else:
                    _, output, errors = ssh_client.exec_command(f'fs sa {self.__BASE_SUBMIT_DIR}/{assignment_name}/{self.student_id} {self.student_id} write')
                    assignments_with_write.append(assignment_name)
            asyncio.run_coroutine_threadsafe(self.maintenance_channel.send(f'\tSubmit Add Student: Added {", ".join(assignments_with_read)} with read access.'), self.main_loop)
            asyncio.run_coroutine_threadsafe(self.maintenance_channel.send(f'\tSubmit Add Student: Added {", ".join(assignments_with_write)} with write access.'), self.main_loop)

            if self.maintenance_channel and self.main_loop:
                asyncio.run_coroutine_threadsafe(self.maintenance_channel.send(f'\tSubmit Add Student: Complete.'), self.main_loop)
        except Exception as e:
            print(e)


@command.command_class
class SubmitAddStudent(command.Command):
    __COMMAND_REGEX = r"!submit\s+add\s+student\s+(?P<student_id>\w+)(\s+(?P<admin>\w+))?"
    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'

    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __UID_FIELD = 'UMBC-Name-Id'
    __NAME_FIELD = 'name'

    permissions = {'student': False, 'ta': False, 'admin': True}

    def run_add_student_thread(self, student_id, assignments):
        AddStudentAssignmentsThread(self.client, student_id, assignments, self.message.channel, asyncio.get_event_loop()).start()

    @command.Command.require_maintenance
    @command.Command.authenticate
    async def handle(self):
        match = re.match(self.__COMMAND_REGEX, self.message.content)
        if not match:
            print('Command did not match regex expression.')
            return

        await self.message.channel.send('Submit Add Student: Starting.')

        submit_col = mongo.db[self.__SUBMIT_SYSTEM_ADMINS]
        if match.group('admin'):
            admin_match = submit_col.find_one({'username': match.group('admin')})
        else:
            admin_match = submit_col.find_one({})

        if not admin_match:
            await self.message.channel.send('Submit Add Student: Unable to find administrator account, terminating.')
            return

        assignments = mongo.db[self.__SUBMIT_ASSIGNMENTS]
        assignment_dict = {assignment[self.__NAME_FIELD]: assignment for assignment in assignments.find()}

        student_uid = match.group('student_id')

        student_col = mongo.db[self.__STUDENTS_GROUP]
        the_student = student_col.find_one({self.__UID_FIELD: student_uid})
        if not the_student:
            await self.message.channel.send(f'Submit Add Student: Unable to find the student {student_uid}')
            return

        await self.message.channel.send('\tStarting Add Student Assignments Thread...')
        self.run_add_student_thread(student_uid, assignment_dict)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if re.match(r"!submit\s+add\s+student\s+(?P<student_id>\w+)(\s+(?P<admin>\w+))?", message.content):
            return True
        return False
