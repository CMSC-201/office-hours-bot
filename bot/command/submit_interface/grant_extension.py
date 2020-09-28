import re
import os
from discord import Message, Client

from paramiko.client import SSHClient
from paramiko import SFTPClient

import command
import mongo
import json
from threading import Thread
from datetime import datetime
from channels import ChannelAuthority
from roles import RoleAuthority


class ExtensionThread(Thread):
    __BASE_SUBMIT_DIR = '/afs/umbc.edu/users/e/r/eric8/pub/cmsc201/fall20'
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
        try:
            sftp_client: SFTPClient = ssh_client.open_sftp()
            sftp_client.put(extension_path, server_extension_path)
            sftp_client.close()

            ssh_client.exec_command('python3 ' + self.__BASE_SUBMIT_DIR + '/admin/grant_extension.py {} {}'.format(server_roster_path, server_extension_path))
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

    __BASE_SUBMIT_DIR = '/afs/umbc.edu/users/e/r/eric8/pub/cmsc201/fall20'
    __ROSTER_NAME = 'submit_roster.csv'
    __EXTENSIONS_NAME = 'extensions.json'
    __MONGO_ID = '_id'

    @staticmethod
    def create_extensions_json(assignments):
        extensions_json = {}
        for assignment in assignments.find():
            extensions_json[assignment['name']] = {'section-extensions': {},
                                                   'student-extensions': {}}

            for student in assignment['student-extensions']:
                due_date = assignment['student-extensions'][student].strftime('%Y.%m.%d.%H.%M.%S')
                if assignment['student-extensions'][student] > datetime.now():
                    extensions_json[assignment['name']]['student-extensions'][student] = due_date
            for section in assignment['section-extensions']:
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
            section_id = match.group('section_id')
            student_id = match.group('student_id')
            due_date = datetime.strptime(' '.join([match.group('due_date'), match.group('due_time')]), '%m-%d-%Y %H:%M:%S')

            if 'student-extensions' not in assignment:
                assignment['student-extensions'] = {}
            if 'section-extensions' not in assignment:
                assignment['section-extensions'] = {}

            if assignment and section_id:
                assignment['section-extensions'][section_id] = due_date
            elif assignment and student_id:
                assignment['student-extensions'][student_id] = due_date

            # update the server side database
            submit_assign.replace_one({self.__MONGO_ID: assignment[self.__MONGO_ID]}, assignment)
            # create new GL side extensions json
            extension_json = self.create_extensions_json(submit_assign)
            # create temporary file to send to the GL server
            extension_path = os.path.join('csv_dump', self.__EXTENSIONS_NAME)
            with open(extension_path, 'w') as json_extensions_file:
                json_extensions_file.write(extension_json)

            await self.message.channel.send('Granting Extension on GL.')
            # We use a separate thread because the discord bot main thread doesn't like it if it takes the scp/ssh commands more than a few seconds to execute.
            ExtensionThread(self.client).start()

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!submit grant extension"):
            return True
        return False



@command.command_class
class GrantAssignmentExtension(command.Command):
    __COMMAND_REGEX = r"!submit\s+(grant|give)\s+extension\s+(?P<assign_name>\w+)\s+((section\s*=\s*(?P<section_id>\w+))|(student\s*=\s*(?P<student_id>\w+)))\s+(?P<due_date>\d{2}-\d{2}-\d{4})\s+(?P<due_time>\d{2}:\d{2}:\d{2})(\s+--admin=(?P<admin>\w+))?"

    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'

    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __UID_FIELD = 'UMBC-Name-Id'

    __BASE_SUBMIT_DIR = '/afs/umbc.edu/users/e/r/eric8/pub/cmsc201/fall20'
    __ROSTER_NAME = 'submit_roster.csv'
    __EXTENSIONS_NAME = 'extensions.json'
    __MONGO_ID = '_id'

    @staticmethod
    def create_extensions_json(assignments):
        extensions_json = {}
        for assignment in assignments.find():
            extensions_json[assignment['name']] = {'section-extensions': {},
                                                   'student-extensions': {}}

            for student in assignment['student-extensions']:
                due_date = assignment['student-extensions'][student].strftime('%Y.%m.%d.%H.%M.%S')
                if assignment['student-extensions'][student] > datetime.now():
                    extensions_json[assignment['name']]['student-extensions'][student] = due_date
            for section in assignment['section-extensions']:
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
            section_id = match.group('section_id')
            student_id = match.group('student_id')
            due_date = datetime.strptime(' '.join([match.group('due_date'), match.group('due_time')]), '%m-%d-%Y %H:%M:%S')

            # update the server side database
            submit_assign.replace_one({self.__MONGO_ID: assignment[self.__MONGO_ID]}, assignment)
            # create new GL side extensions json
            extension_json = self.create_extensions_json(submit_assign)
            # create temporary file to send to the GL server
            extension_path = os.path.join('csv_dump', self.__EXTENSIONS_NAME)
            with open(extension_path, 'w') as json_extensions_file:
                json_extensions_file.write(extension_json)
            await self.message.channel.send('Granting Extension on GL.')
            # We use a separate thread because the discord bot main thread doesn't like it if it takes the scp/ssh commands more than a few seconds to execute.
            ExtensionThread(self.client).start()


    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!submit grant assignment extension"):
            return True
        return False
