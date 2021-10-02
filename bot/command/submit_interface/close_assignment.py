__DOCSTRING__ = """
    
"""

import re
import json
import os
from datetime import datetime, timedelta
from discord import Message, Client

from pymongo.results import InsertOneResult, UpdateResult, DeleteResult

import command
import mongo
import globals

from channels import ChannelAuthority
from roles import RoleAuthority


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

    def close_assignment(self, assignment_name):
        assignment = self.assignments.find_one({'name': assignment_name})

        if not assignment:
            # await self.client.channel_authority.maintenance_channel.send('Assignment {} was not found. '.format(assignment_name))
            print('Assignment {} was not found. '.format(assignment_name))
            return

        print('running close assignment script')

        self.write_roster()

        extensions_json = {}
        if not os.path.exists('csv_dump'):
            os.makedirs('csv_dump')
        with open(os.path.join('csv_dump', self.__EXTENSIONS_NAME), 'w') as json_extensions_file:
            for assignment in self.assignments.find():
                extensions_json[assignment['name']] = {'section-extensions': {},
                                                       'student-extensions': {}}

                for student in assignment['student-extensions']:
                    print(assignment['student-extensions'][student])
                    due_date = assignment['student-extensions'][student]['due-date'].strftime('%Y.%m.%d.%H.%M.%S')
                    if assignment['student-extensions'][student]['due-date'] > datetime.now():
                        extensions_json[assignment['name']]['student-extensions'][student] = due_date
                for section in assignment['section-extensions']:
                    due_date = assignment['section-extensions'][section]['due-date'].strftime('%Y.%m.%d.%H.%M.%S')
                    extensions_json[assignment['name']]['section-extensions'][section] = due_date

            json_extensions_file.write(json.dumps(extensions_json, indent='\t'))

        ssh_client = self.connect_ssh()
        ftp_client = ssh_client.open_sftp()
        ftp_client.put(os.path.join('csv_dump', self.__ROSTER_NAME), self.__BASE_SUBMIT_DIR + '/admin/' + self.__ROSTER_NAME)
        ftp_client.put(os.path.join('csv_dump', self.__EXTENSIONS_NAME), self.__BASE_SUBMIT_DIR + '/admin/' + self.__EXTENSIONS_NAME)
        ftp_client.close()

        roster_path = self.__BASE_SUBMIT_DIR + '/admin/' + self.__ROSTER_NAME
        extensions_path = self.__BASE_SUBMIT_DIR + '/admin/' + self.__EXTENSIONS_NAME
        print('python3 ' + self.__BASE_SUBMIT_DIR + self.__ADMIN__CLOSE_ASSIGNMENT.format(assignment_name, roster_path, extensions_path))
        self.ssh_client.exec_command('python3 ' + self.__BASE_SUBMIT_DIR + self.__ADMIN__CLOSE_ASSIGNMENT.format(assignment_name, roster_path, extensions_path))
        self.assignments.update_one({'name': assignment_name}, {'$set': {'open': False}})

    async def handle(self):
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        ra: RoleAuthority = RoleAuthority(self.guild)
        if ra.is_admin(self.message.author) and ca.is_maintenance_channel(self.message.channel):
            match = re.match(self.__COMMAND_REGEX, self.message.content)
            submit_col = mongo.db[self.__SUBMIT_SYSTEM_ADMINS]
            assignments = mongo.db[self.__SUBMIT_ASSIGNMENTS]

            # keep this for when we need to update on the server.
            if match.group('admin'):
                admin_match = submit_col.find_one({'username': match.group('admin')})
            else:
                admin_match = submit_col.find_one({})

            assignment_name = match.group('assign_name')

            self.close_assignment(assignment_name)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if re.match(r"!submit\s+close\s+(?P<assign_name>\w+)(\s+(?P<admin>--admin=\w+))?", message.content):
            return True
        return False
