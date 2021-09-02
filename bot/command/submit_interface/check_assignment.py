import re
from datetime import datetime, timedelta
from discord import Message, Client

from pymongo.results import InsertOneResult, UpdateResult, DeleteResult

import command
import mongo
from channels import ChannelAuthority
from roles import RoleAuthority
from threading import Thread
import asyncio


class CheckAssignmentThread(Thread):
    __BASE_SUBMIT_DIR = '/afs/umbc.edu/users/e/r/eric8/pub/cmsc201/fall21'
    __MESSAGE = 'Your {} assignment is:\n```{}```'
    __MESSAGE_CANNOT_FIND = 'I couldn\'t find the assignment you asked for: {}'
    __USERNAME = 'UMBC-Name-Id'

    def __init__(self, client, recipient, user, assignment, problem_file_name):
        super().__init__(daemon=True)
        self.client = client
        self.user = user
        self.recipient = recipient
        self.assignment = assignment
        self.problem_file_name = problem_file_name
        self.event_loop = asyncio.get_event_loop()

    def run(self):
        ssh_client = self.client.submit_daemon.connect_ssh()
        _, stdout, stderr = ssh_client.exec_command('cat ' + '/'.join([self.__BASE_SUBMIT_DIR, self.assignment, self.user[self.__USERNAME], self.problem_file_name]))
        error_report = stderr.read()
        if error_report:
            asyncio.run_coroutine_threadsafe(self.recipient.send(self.__MESSAGE_CANNOT_FIND.format(self.assignment)), self.event_loop)
            print(error_report)
        else:
            program_snippet: str = stdout.read(1000).decode('utf-8')
            asyncio.run_coroutine_threadsafe(self.recipient.send(self.__MESSAGE.format(self.assignment, program_snippet)), self.event_loop)


@command.command_class
class CheckAssignment(command.Command):
    __COMMAND_REGEX = r"!submit\s+check\s+(?P<assignment>\w+)\s+(?P<problem_file>(\w|_|\.)+)(\s+user=(P<user>\w+))?"
    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'

    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'

    __DISCORD_ID = 'discord'

    def find_user(self, discord_id):
        students_group = mongo.db[self.__STUDENTS_GROUP]
        ta_group = mongo.db[self.__TA_GROUP]
        admin_group = mongo.db[self.__ADMIN_GROUP]

        for group in [students_group, ta_group, admin_group]:
            person = group.find_one({self.__DISCORD_ID: self.message.author.id})
            if person:
                return person
        return None

    async def handle(self):
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        ra: RoleAuthority = RoleAuthority(self.guild)

        match = re.match(self.__COMMAND_REGEX, self.message.content)
        if match:


            submit_col = mongo.db[self.__SUBMIT_SYSTEM_ADMINS]
            assignments = mongo.db[self.__SUBMIT_ASSIGNMENTS]

            # keep this for when we need to update on the server.
            if False:  # match.group('admin'):
                admin_match = submit_col.find_one({'username': match.group('admin')})
            else:
                admin_match = submit_col.find_one()

            assignment_name = match.group('assignment')
            problem_file_name = match.group('problem_file')

            the_user = self.find_user(self.message.author)
            assignment = assignments.find_one({'name': assignment_name})
            print('assignment found', assignment_name, problem_file_name)
            print(assignment, the_user)

            if ra.ta_or_higher(self.message.author):
                # allow access to all submissions
                await self.message.author.send("I'm about to go looking for you, please be patient... ")
                search_user = match.group('user')
                CheckAssignmentThread(self.client, self.message.author, the_user, assignment_name, problem_file_name).start()
            else:
                # only allow access to their own submissions
                await self.message.author.send("I'm about to go looking for you, please be patient... ")
                CheckAssignmentThread(self.client, self.message.author, the_user, assignment_name, problem_file_name).start()

        if self.message.guild:
            await self.message.delete(delay=5)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if re.match(r"!submit\s+check\s+(?P<assignment>\w+)\s+(?P<problem_file>(\w|_|\.)+)(\s+(P<user>\w+))?", message.content):
            return True
        return False
