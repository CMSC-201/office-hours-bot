import re
import os
import csv
import globals
from datetime import datetime, timedelta
from discord import Message, Client

from pymongo.results import InsertOneResult, UpdateResult

import command
import mongo
import asyncio
from asyncio import Lock
from paramiko.client import SSHClient
from paramiko import SFTPClient
from channels import ChannelAuthority

from threading import Thread


class AssignmentCreationThread(Thread):
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __USERNAME = 'UMBC-Name-Id'
    __SECTION = 'Section'

    __ROSTER_NAME = 'submit_roster.csv'
    __BASE_SUBMIT_DIR = globals.get_globals()['props']['base_submit_dir']

    def __init__(self, guild, client, assignment_name, due_time, message_loop):
        super().__init__(daemon=True)
        self.assignment_name = assignment_name
        self.guild = guild
        self.client = client
        self.due_time = due_time
        self.channel_authority: ChannelAuthority = ChannelAuthority(self.guild)
        self.message_loop = message_loop

    def async_message_send(self, message):
        asyncio.run_coroutine_threadsafe(self.channel_authority.maintenance_channel.send(message), self.message_loop)

    def run(self):
        ssh_client: SSHClient = self.client.submit_daemon.connect_ssh()
        students_group = mongo.db[self.__STUDENTS_GROUP]
        ta_group = mongo.db[self.__TA_GROUP]
        admin_group = mongo.db[self.__ADMIN_GROUP]

        ftp_client: SFTPClient = ssh_client.open_sftp()

        if not os.path.exists('csv_dump'):
            self.async_message_send('\tCreating new csv_dump directory. ')
            os.makedirs('csv_dump')

        with open(os.path.join('csv_dump', self.__ROSTER_NAME), 'w', newline='') as csv_file:
            roster = csv.writer(csv_file)
            roster_list = [[student[self.__USERNAME], student[self.__SECTION]] for student in students_group.find()]
            roster_list.extend([[ta[self.__USERNAME], ta[self.__SECTION]] for ta in ta_group.find()])
            roster_list.extend([[admin[self.__USERNAME], 0] for admin in admin_group.find()])
            roster.writerows(roster_list)
            self.async_message_send('\tWriting New Roster. ')

        self.async_message_send('\tFTP: Pushing New Roster... ')
        ftp_client.put(os.path.join('csv_dump', self.__ROSTER_NAME), self.__BASE_SUBMIT_DIR + '/admin/' + self.__ROSTER_NAME)
        ftp_client.close()
        self.async_message_send('\tFTP: Complete')

        self.async_message_send('\tExecuting create assignment on GL server.  ')
        ssh_client.exec_command(f'python3 {self.__BASE_SUBMIT_DIR}/admin/create_assignment.py {self.assignment_name} {self.__BASE_SUBMIT_DIR + "/admin/" + self.__ROSTER_NAME} {self.due_time.strftime("%m/%d/%Y")}')
        self.async_message_send('\tComplete.')


@command.command_class
class ConfigureAssignment(command.Command):
    __COMMAND_REGEX = r"!submit\s+configure\s+(?P<assign_name>(\w|-)+)\s+(?P<due_date>\d{2}-\d{2}-\d{4})\s+(?P<due_time>\d{2}:\d{2}:\d{2})(\s+(?P<no_create>--nocreate))?"
    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'

    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __UID_FIELD = 'UMBC-Name-Id'

    permissions = {'student': False, 'ta': False, 'admin': True}

    def create_assignment_on_GL(self, assignment_name, due_date):
        AssignmentCreationThread(self.guild, self.client, assignment_name, due_date, asyncio.get_event_loop()).start()

    @command.Command.require_maintenance
    @command.Command.authenticate
    async def handle(self):
        match = re.match(self.__COMMAND_REGEX, self.message.content)
        if not match:
            print('Some kind of match error')
            return

        self.client.submit_daemon.creation_lock: Lock
        async with self.client.submit_daemon.creation_lock:
            assignments = mongo.db[self.__SUBMIT_ASSIGNMENTS]
            assignment_name = match.group('assign_name')
            due_date = datetime.strptime(' '.join([match.group('due_date'), match.group('due_time')]), '%m-%d-%Y %H:%M:%S')
            duplicate = assignments.find_one({'name': assignment_name})
            if duplicate:
                if duplicate['due-date'] == due_date:
                    await self.message.channel.send('There is a duplicate assignment')
                else:
                    await self.message.channel.send(f'Updating due date for {assignment_name} to {due_date.strftime("%m-%d-%Y %H:%M:%S")}')
                    assignments.update_one({'name': assignment_name}, {'$set': {'due-date': due_date}})
            else:
                await self.message.channel.send(f'Configuring Assignment {assignment_name}...')
                ir = assignments.insert_one({'name': assignment_name, 'due-date': due_date, 'open': True, 'student-extensions': {}, 'section-extensions': {}})
                if ir.inserted_id:
                    await self.message.channel.send(f'Assignment {assignment_name} added to database.')
                    if not match.group('no_create'):
                        await self.message.channel.send(f'Starting assignment {assignment_name} creation thread.')
                        self.create_assignment_on_GL(assignment_name, due_date)
                    else:
                        await self.message.channel.send(f'Assignment {assignment_name} GL creation skipped.')
                else:
                    await self.message.channel.send(f'Error: Assignment {assignment_name} not added to database.')

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if re.match(r"!submit\s+configure\s+(?P<assign_name>(\w|-)+)\s+(?P<due_date>\d{2}-\d{2}-\d{4})\s+(?P<due_time>\d{2}:\d{2}:\d{2})(\s+(?P<admin>--admin=\w+))?", message.content):
            return True
        return False
