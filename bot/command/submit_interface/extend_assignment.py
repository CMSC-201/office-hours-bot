import re
import os
from discord import Message, Client, User

from paramiko.client import SSHClient
from paramiko import SFTPClient

import command
import mongo
import json
import asyncio
from threading import Thread
from datetime import datetime
from channels import ChannelAuthority
from roles import RoleAuthority


class AssignmentExtensionThread(Thread):
    __BASE_SUBMIT_DIR = '/afs/umbc.edu/users/e/r/eric8/pub/cmsc201/fall21'
    __ROSTER_NAME = 'submit_roster.csv'
    __EXTENSIONS_NAME = 'extensions.json'

    def __init__(self, client, assignment_name):
        super().__init__(daemon=True)
        self.client = client
        self.assignment_name = assignment_name

    def run(self):
        ssh_client: SSHClient = self.client.submit_daemon.connect_ssh()
        try:
            ssh_client.exec_command('python3 ' + self.__BASE_SUBMIT_DIR + '/admin/extend_assignment.py {}'.format(self.assignment_name))
        except Exception as e:
            print(e)


@command.command_class
class GrantAssignmentExtension(command.Command):
    __COMMAND_REGEX = r"!submit\s+extend\s+(assignment\s*=\s*(?P<assign_name>\w+))\s+(?P<due_date>\d{2}-\d{2}-\d{4})\s+(?P<due_time>\d{2}:\d{2}:\d{2})"

    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'

    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __UID_FIELD = 'UMBC-Name-Id'
    __SECTION = 'Section'

    __BASE_SUBMIT_DIR = '/afs/umbc.edu/users/e/r/eric8/pub/cmsc201/fall21'
    __ROSTER_NAME = 'submit_roster.csv'
    __EXTENSIONS_NAME = 'extensions.json'
    __MONGO_ID = '_id'
    __DISCORD_ID = 'discord'
    __FIRST_NAME = 'First-Name'
    __LAST_NAME = 'Last-Name'

    @staticmethod
    def create_extensions_json(assignments, new_due_date):
        extensions_json = {}
        for assignment in assignments.find():
            extensions_json[assignment['name']] = {'section-extensions': {},
                                                   'student-extensions': {}}

            for student in assignment['student-extensions']:
                due_date = assignment['student-extensions'][student]['due-date'].strftime('%Y.%m.%d.%H.%M.%S')
                if assignment['student-extensions'][student]['due-date'] > new_due_date:
                    extensions_json[assignment['name']]['student-extensions'][student] = due_date
                else:
                    assignment['student-extensions'][student]['open'] = False
            for section in assignment['section-extensions']:
                due_date = assignment['section-extensions'][section]['due-date'].strftime('%Y.%m.%d.%H.%M.%S')
                if assignment['section-extensions'][section]['due-date'] > new_due_date:
                    extensions_json[assignment['name']]['section-extensions'][section]['due-date'] = due_date
                else:
                    assignment['section-extensions'][section]['open'] = False

        return json.dumps(extensions_json, indent='\t')

    async def handle(self):
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        ra: RoleAuthority = RoleAuthority(self.guild)
        if ra.is_admin(self.message.author) and ca.is_maintenance_channel(self.message.channel):
            match = re.match(self.__COMMAND_REGEX, self.message.content)
            if not match:
                await self.message.channel.send("Usage: !submit extend assignment=[assignment name] [due date format MM-DD-YYYY HH:MM:SS]")
                return
            submit_assign = mongo.db[self.__SUBMIT_ASSIGNMENTS]
            assignment_name = match.group('assign_name')
            assignment = submit_assign.find_one({'name': match.group('assign_name')})
            if assignment:
                due_date = datetime.strptime(' '.join([match.group('due_date'), match.group('due_time')]), '%m-%d-%Y %H:%M:%S')
                # update the server side database
                assignment['due-date'] = due_date
                # reopen the assignment if it's closed.
                assignment['open'] = True

                submit_assign.replace_one({self.__MONGO_ID: assignment[self.__MONGO_ID]}, assignment)
                # create new GL side extensions json
                extension_json = self.create_extensions_json(submit_assign, due_date)
                # create temporary file to send to the GL server
                if not os.path.exists('csv_dump'):
                    os.makedirs('csv_dump')
                extension_path = os.path.join('csv_dump', self.__EXTENSIONS_NAME)
                AssignmentExtensionThread(self.client, assignment_name).start()
                with open(extension_path, 'w') as json_extensions_file:
                    json_extensions_file.write(extension_json)
                await self.message.channel.send('Granting Extension for {} on GL until {}.'.format(assignment_name, due_date))
            # We use a separate thread because the discord bot main thread doesn't like it if it takes the scp/ssh commands more than a few seconds to execute.

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        __COMMAND_REGEX = r"!submit\s+extend\s+(assignment\s*=\s*(?P<assign_name>\w+))\s+(?P<due_date>\d{2}-\d{2}-\d{4})\s+(?P<due_time>\d{2}:\d{2}:\d{2})"
        if re.match(__COMMAND_REGEX, message.content):
            return True
        return False
