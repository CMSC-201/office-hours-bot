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


class ExtensionThread(Thread):
    __BASE_SUBMIT_DIR = '/afs/umbc.edu/users/e/r/eric8/pub/cmsc201/fall21'
    __ROSTER_NAME = 'submit_roster.csv'
    __EXTENSIONS_NAME = 'extensions.json'

    def __init__(self, client):
        super().__init__(daemon=True)
        self.client = client

    def run(self):
        extension_path = os.path.join('csv_dump', self.__EXTENSIONS_NAME)
        # open the sftp connection and transfer the file to the GL server.
        ssh_client: SSHClient = self.client.submit_daemon.connect_ssh()
        server_roster_path = self.__BASE_SUBMIT_DIR + '/admin/' + self.__ROSTER_NAME
        server_extension_path = self.__BASE_SUBMIT_DIR + '/admin/' + self.__EXTENSIONS_NAME
        # ca: ChannelAuthority = ChannelAuthority()
        try:
            sftp_client: SFTPClient = ssh_client.open_sftp()
            sftp_client.put(extension_path, server_extension_path)
            sftp_client.close()

            ssh_client.exec_command('python3 ' + self.__BASE_SUBMIT_DIR + '/admin/grant_extension.py {} {}'.format(server_roster_path, server_extension_path))
            # maintenance_channel = ca.get_maintenance_channel()

            # asyncio.run(maintenance_channel.send('SSH Command Executed, Extension Granted'))
        except Exception as e:
            print(e)


@command.command_class
class GrantIndividualExtension(command.Command):
    __COMMAND_REGEX = r"!submit\s+(grant|give)\s+extension\s+(?P<assign_name>\w+)\s+((section\s*=\s*(?P<section_id>\w+))|(student\s*=\s*(?P<student_id>\w+)))\s+(?P<due_date>\d{2}-\d{2}-\d{4})\s+(?P<due_time>\d{2}:\d{2}:\d{2})(\s+--admin=(?P<admin>\w+))?"

    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'

    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __UID_FIELD = 'UMBC-Name-Id'

    __BASE_SUBMIT_DIR = '/afs/umbc.edu/users/e/r/eric8/pub/cmsc201/fall21'
    __ROSTER_NAME = 'submit_roster.csv'
    __EXTENSIONS_NAME = 'extensions.json'
    __MONGO_ID = '_id'
    __DISCORD_ID = 'discord'
    __FIRST_NAME = 'First-Name'
    __LAST_NAME = 'Last-Name'
    __SECTION = 'Section'

    @staticmethod
    def create_extensions_json(assignments):
        extensions_json = {}
        for assignment in assignments.find():
            extensions_json[assignment['name']] = {'section-extensions': {},
                                                   'student-extensions': {}}

            for student in assignment['student-extensions']:
                if isinstance(assignment['student-extensions'][student], dict):
                    # old database entries are simply datetime objects rather than dictionaries with the due-date, open, name, and student/section
                    if assignment['student-extensions'][student].get('open', True):
                        due_date = assignment['student-extensions'][student]['due-date'].strftime('%Y.%m.%d.%H.%M.%S')
                        extensions_json[assignment['name']]['student-extensions'][student] = due_date
                else:
                    # old database compatibility
                    due_date = assignment['student-extensions'][student].strftime('%Y.%m.%d.%H.%M.%S')
                    extensions_json[assignment['name']]['student-extensions'][student] = due_date
            for section in assignment['section-extensions']:
                if isinstance(assignment['section-extensions'][section], dict):
                    due_date = assignment['section-extensions'][section]['due-date'].strftime('%Y.%m.%d.%H.%M.%S')
                    if assignment['section-extensions'][section]['open']:
                        extensions_json[assignment['name']]['section-extensions'][section] = due_date
                else:
                    # old database compatibility
                    due_date = assignment['section-extensions'][section].strftime('%Y.%m.%d.%H.%M.%S')
                    extensions_json[assignment['name']]['section-extensions'][section] = due_date


        return json.dumps(extensions_json, indent='\t')

    async def handle(self):
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        ra: RoleAuthority = RoleAuthority(self.guild)
        if ra.is_admin(self.message.author) and ca.is_maintenance_channel(self.message.channel):
            match = re.match(self.__COMMAND_REGEX, self.message.content)
            if not match:
                await self.message.channel.send("Usage: ...")
                return
            submit_col = mongo.db[self.__SUBMIT_SYSTEM_ADMINS]
            if match.group('admin'):
                admin_match = submit_col.find_one({'username': match.group('admin')})
            else:
                admin_match = submit_col.find_one({})
            if not admin_match:
                await self.message.channel.send('Unable to find administrator account, terminating.')
                return

            submit_assign = mongo.db[self.__SUBMIT_ASSIGNMENTS]
            assignment = submit_assign.find_one({'name': match.group('assign_name')})
            if not assignment:
                await self.message.channel.send('Assignment {} not found'.format(match.group('assign_name')))
                return
            section_id = match.group('section_id')
            student_id = match.group('student_id')
            due_date = datetime.strptime(' '.join([match.group('due_date'), match.group('due_time')]), '%m-%d-%Y %H:%M:%S')

            if 'student-extensions' not in assignment:
                assignment['student-extensions'] = {}
            if 'section-extensions' not in assignment:
                assignment['section-extensions'] = {}

            if assignment and section_id:
                assignment['section-extensions'][section_id] = {'section': section_id, 'due-date': due_date, 'name': assignment['name'], 'open': True}
            elif assignment and student_id:
                assignment['student-extensions'][student_id] = {'student': student_id, 'due-date': due_date, 'name': assignment['name'], 'open': True}

            # update the server side database
            submit_assign.replace_one({self.__MONGO_ID: assignment[self.__MONGO_ID]}, assignment)
            # create new GL side extensions json
            extension_json = self.create_extensions_json(submit_assign)
            # create temporary file to send to the GL server

            if not os.path.exists('csv_dump'):
                os.makedirs('csv_dump')
            extension_path = os.path.join('csv_dump', self.__EXTENSIONS_NAME)
            with open(extension_path, 'w') as json_extensions_file:
                json_extensions_file.write(extension_json)

            await self.message.channel.send('Granting Extension on GL.')
            # We use a separate thread because the discord bot main thread doesn't like it if it takes the scp/ssh commands more than a few seconds to execute.
            ExtensionThread(self.client).start()

            # find and message the TA that an extension has been granted for a student
            student_col = mongo.db[self.__STUDENTS_GROUP]
            ta_collection = mongo.db[self.__TA_GROUP]

            if student_id:
                the_student = student_col.find_one({self.__UID_FIELD: student_id})
                the_student_name = ' '.join([the_student[self.__FIRST_NAME], the_student[self.__LAST_NAME]])
                for ta in ta_collection.find({self.__SECTION: the_student[self.__SECTION]}):
                    ta_discord_user: User = await self.client.fetch_user(ta[self.__DISCORD_ID])
                    message = '{} ({}) has been granted an extension until {} for assignment {}.'.format(the_student_name, student_id, due_date.strftime('%m-%d-%Y %H:%M:%S'), assignment['name'])
                    await self.safe_send(ta_discord_user, message)
            # if it's a section extension, send the TA an update on their section's extension
            elif section_id:
                for ta in ta_collection.find({self.__SECTION: section_id}):
                    ta_discord_user: User = await self.client.fetch_user(ta[self.__DISCORD_ID])
                    message = 'Your section has been granted an extension until {} for assignment {}.'.format(due_date.strftime('%m-%d-%Y %H:%M:%S'), assignment['name'])
                    await self.safe_send(ta_discord_user, message)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!submit grant extension"):
            return True
        return False

