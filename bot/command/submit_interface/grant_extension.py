import re
import os
import logging
from discord import Message, Client, User

from paramiko.client import SSHClient
from paramiko import SFTPClient

import command
import globals
import mongo
import json
import asyncio
from threading import Thread
from datetime import datetime
from channels import ChannelAuthority


logger = logging.getLogger('bot_main')


class ExtensionThread(Thread):
    __BASE_SUBMIT_DIR = globals.get_globals()['props']['base_submit_dir']
    __ROSTER_NAME = 'submit_roster.csv'
    __EXTENSIONS_NAME = 'extensions.json'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'

    def __init__(self, client, maintenance_channel=None, main_loop=None, assignments=None, **kwargs):
        super().__init__(daemon=True)
        self.client = client
        self.maintenance_channel = maintenance_channel
        self.main_loop = main_loop
        self.assignments = assignments if assignments is not None else mongo.db[self.__SUBMIT_ASSIGNMENTS]
        self.debug_level = kwargs.get('debug_level', 0)

    @staticmethod
    def create_extensions_json(assignments):
        extensions_json = {}

        for assignment in assignments.find():
            extensions_json[assignment['name']] = {'section-extensions': {}, 'student-extensions': {}}

            for student in assignment['student-extensions']:
                due_date = assignment['student-extensions'][student]['due-date'].strftime('%Y.%m.%d.%H.%M.%S')
                if assignment['student-extensions'][student]['due-date'] > datetime.now():
                    extensions_json[assignment['name']]['student-extensions'][student] = due_date
            for section in assignment['section-extensions']:
                due_date = assignment['section-extensions'][section]['due-date'].strftime('%Y.%m.%d.%H.%M.%S')
                if assignment['section-extensions'][section]['due-date'] > datetime.now():
                    extensions_json[assignment['name']]['section-extensions'][section] = due_date

        return json.dumps(extensions_json, indent='\t')

    def write_extension_file(self, assignments):
        extension_json = self.create_extensions_json(assignments)
        extension_path = os.path.join('csv_dump/', 'extensions.json')

        if not os.path.exists('csv_dump'):
            os.makedirs('csv_dump')

        with open(extension_path, 'w') as extension_file:
            extension_file.write(extension_json)
        return extension_path

    def send_maintenance_message(self, message):
        if self.maintenance_channel and self.main_loop:
            asyncio.run_coroutine_threadsafe(self.maintenance_channel.send(message), self.main_loop)

    def run(self):
        if self.debug_level >= 1:
            logger.info('Extension SSH Login Starting')
        ssh_client: SSHClient = self.client.submit_daemon.connect_ssh()
        if self.debug_level >= 1:
            logger.info('Extension SSH Login Complete')
        server_roster_path = os.path.join(self.__BASE_SUBMIT_DIR, 'admin', self.__ROSTER_NAME)
        server_extension_path = os.path.join(self.__BASE_SUBMIT_DIR, 'admin', self.__EXTENSIONS_NAME)
        try:
            extension_path = self.write_extension_file(self.assignments)
            if self.debug_level >= 2:
                logger.info(f'Extension Path {extension_path}')

            if self.debug_level >= 1:
                logger.info('Starting FTP of Extension File')
            sftp_client: SFTPClient = ssh_client.open_sftp()
            sftp_client.put(extension_path, server_extension_path)
            sftp_client.close()
            if self.debug_level >= 1:
                logger.info('Ending FTP of Extension File, Executing server command to extend')

            _, output, errors = ssh_client.exec_command(f'python {os.path.join(self.__BASE_SUBMIT_DIR, "admin", "grant_extension.py")} {server_roster_path} {server_extension_path}')

            if self.debug_level >= 1:
                logger.info('Extension Command sent to server.')

            logging.info(output.read())
            logging.info(errors.read())

            self.send_maintenance_message(f'Extension Thread: SSH Command Executed, Extension Granted on Server')
        except Exception as e:
            if self.maintenance_channel and self.main_loop:
                asyncio.run_coroutine_threadsafe(self.maintenance_channel.send(e), self.main_loop)


@command.command_class
class GrantIndividualExtension(command.Command):
    __COMMAND_REGEX = r"!submit\s+(grant|give)\s+extension\s+(?P<assign_name>\w+)\s+((section\s*=\s*(?P<section_id>\w+))|(student\s*=\s*(?P<student_id>\w+)))\s+(?P<due_date>\d{2}-\d{2}-\d{4})\s+(?P<due_time>\d{2}:\d{2}:\d{2})(\s+--debug-level\s*=\s*(?P<debug_level>\d+))?"

    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'

    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __UID_FIELD = 'UMBC-Name-Id'

    __BASE_SUBMIT_DIR = globals.get_globals()['props']['base_submit_dir']
    __ROSTER_NAME = 'submit_roster.csv'
    __EXTENSIONS_NAME = 'extensions.json'
    __MONGO_ID = '_id'
    __DISCORD_ID = 'discord'
    __FIRST_NAME = 'First-Name'
    __LAST_NAME = 'Last-Name'
    __SECTION = 'Section'

    permissions = {'student': False, 'ta': False, 'admin': True}

    @command.Command.authenticate
    @command.Command.require_maintenance
    async def handle(self):
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        match = re.match(self.__COMMAND_REGEX, self.message.content)
        if not match:
            await self.message.channel.send("Usage: !submit grant extension [assignment] [student=[student_username]] [section=section_number] [MM-DD-YYYY] [HH:MM:SS]")
            return
        submit_col = mongo.db[self.__SUBMIT_SYSTEM_ADMINS]

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
        debug_level = int(match.group('debug_level')) if match.group('debug_level') else 0
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
        the_extension_thread = ExtensionThread(self.client, ca.get_maintenance_channel(), asyncio.get_event_loop(), submit_assign, debug_level=debug_level)

        # find and message the TA that an extension has been granted for a student
        student_col = mongo.db[self.__STUDENTS_GROUP]
        ta_collection = mongo.db[self.__TA_GROUP]
        admin_collection = mongo.db[self.__ADMIN_GROUP]

        await self.message.channel.send('Starting Extension Process...')
        # We use a separate thread because the discord bot main thread doesn't like it if it takes the scp/ssh commands more than a few seconds to execute.
        the_extension_thread.start()

        if student_id:
            the_student = student_col.find_one({self.__UID_FIELD: student_id})
            if the_student:

                the_student_name = ' '.join([the_student[self.__FIRST_NAME], the_student[self.__LAST_NAME]])
                message = f'{the_student_name} ({student_id}) will be granted an extension until {due_date.strftime("%m-%d-%Y %H:%M:%S")} for assignment {assignment["name"]}. \n Extension is granted if the next message appears. '
                await ca.get_maintenance_channel().send(message)

                for admin in admin_collection.find({self.__SECTION: the_student[self.__SECTION]}):
                    ta_discord_user: User = await self.client.fetch_user(admin[self.__DISCORD_ID])
                    await self.safe_send(ta_discord_user, message)

                for ta in ta_collection.find({self.__SECTION: the_student[self.__SECTION]}):
                    ta_discord_user: User = await self.client.fetch_user(ta[self.__DISCORD_ID])
                    await self.safe_send(ta_discord_user, message)
            else:
                await self.message.channel.send('Unable to find the student {}, no extension was granted. '.format(student_id))
        # if it's a section extension, send the TA an update on their section's extension
        elif section_id:
            message = f'Your section will be granted an extension until {due_date.strftime("%m-%d-%Y %H:%M:%S")} for assignment {assignment["name"]}.\n Extension is granted if the next message appears. '

            for admin in admin_collection.find({self.__SECTION: section_id}):
                ta_discord_user: User = await self.client.fetch_user(admin[self.__DISCORD_ID])
                await self.safe_send(ta_discord_user, message)

            for ta in ta_collection.find({self.__SECTION: section_id}):
                ta_discord_user: User = await self.client.fetch_user(ta[self.__DISCORD_ID])
                await self.safe_send(ta_discord_user, message)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        __COMMAND_REGEX = r"!submit\s+(grant|give)\s+extension\s+(?P<assign_name>\w+)\s+((section\s*=\s*(?P<section_id>\w+))|(student\s*=\s*(?P<student_id>\w+)))\s+(?P<due_date>\d{2}-\d{2}-\d{4})\s+(?P<due_time>\d{2}:\d{2}:\d{2})(\s+--debug-level\s*=\s*(?P<debug_level>\d+))?"
        if re.match(__COMMAND_REGEX, message.content):
            return True
        return False
