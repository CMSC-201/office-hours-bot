import asyncio
import re
from datetime import datetime, timedelta
from discord import Message, Client
import command
import mongo
import globals
from channels import ChannelAuthority
from submit_interface.grant_extension import ExtensionThread


@command.command_class
class RequestExtension(command.Command):

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
    __EXTENSION_LIMIT_STR = 'Extensions-Received'

    __STUDENT_EXT = 'student-extensions'
    __SECTION_EXT = 'section-extensions'
    __ASSIGNMENT_NAME = 'name'
    __DUE_DATE = 'due-date'
    __OPEN = 'open'

    __EXTENSION_LIMIT = 2

    permissions = {'student': True, 'ta': True, 'admin': True}

    @command.Command.authenticate
    async def handle(self):

        assignment_name = re.match(r"!submit\s+request\s+extension\s+(?P<assign_name>\w+)(\s+--override)?", self.message.content).group('assign_name')
        override_flag = False
        if '--override' in self.message.content:
            override_flag = True

        students_group = mongo.db[self.__STUDENTS_GROUP]
        ta_group = mongo.db[self.__TA_GROUP]
        admin_group = mongo.db[self.__ADMIN_GROUP]

        the_student = students_group.find_one({self.__DISCORD_ID: self.message.author.id})
        the_ta = ta_group.find_one({self.__DISCORD_ID: self.message.author.id})
        the_admin = admin_group.find_one({self.__DISCORD_ID: self.message.author.id})

        assignments = mongo.db[self.__SUBMIT_ASSIGNMENTS]

        if not any([the_student, the_ta, the_admin]):
            await self.message.author.send('Unable to find you in student, ta, or admin groups.  You should talk to an administrator to fix this.  ')
            return False

        the_assignment = assignments.find_one({self.__ASSIGNMENT_NAME: assignment_name})
        if not the_assignment:
            await self.message.author.send(f'Unable to find {assignment_name} in the list of assignments.  ')
            return False

        if datetime.now() > the_assignment[self.__DUE_DATE] + timedelta(days=2) and (not override_flag and the_admin):
            await self.message.author.send('The due date has been exceeded by two days at least.  Talk to your professor about your circumstances. ')
            return False

        if the_student:
            student_id = the_student[self.__UID_FIELD]
            if self.__EXTENSION_LIMIT_STR not in the_student or the_student[self.__EXTENSION_LIMIT_STR] < self.__EXTENSION_LIMIT:
                students_group.update_one({self.__MONGO_ID: the_student[self.__MONGO_ID]}, {'$set': {self.__EXTENSION_LIMIT_STR: the_student.get(self.__EXTENSION_LIMIT_STR, 0) + 1}})
            else:
                await self.message.author.send('You have reached the number of allowed extensions for the semester. You need to contact your Professor for an extension. ')
                return False
        elif the_ta:
            student_id = the_ta[self.__UID_FIELD]
            ta_group.update_one({self.__MONGO_ID: the_ta[self.__MONGO_ID]}, {'$set': {self.__EXTENSION_LIMIT_STR: the_ta.get(self.__EXTENSION_LIMIT_STR, 0) + 1}})
        else:
            student_id = the_admin[self.__UID_FIELD]
            admin_group.update_one({self.__MONGO_ID: the_admin[self.__MONGO_ID]}, {'$set': {self.__EXTENSION_LIMIT_STR: the_admin.get(self.__EXTENSION_LIMIT_STR, 0) + 1}})

        the_assignment['student-extensions'][student_id] = {'student': student_id, 'due-date': the_assignment[self.__DUE_DATE] + timedelta(days=2), 'name': the_assignment['name'], 'open': True}
        assignments.replace_one({self.__MONGO_ID: the_assignment[self.__MONGO_ID]}, the_assignment)

        ca: ChannelAuthority = ChannelAuthority(self.guild)
        extension_thread = ExtensionThread(self.client, ca.get_maintenance_channel(), asyncio.get_event_loop(), assignments)
        extension_thread.start()

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if re.match(r"!submit\s+request\s+extension\s+(?P<assign_name>\w+)", message.content):
            return True

        return False

    @staticmethod
    async def is_invoked_by_direct_message(message: Message, client: Client):
        if re.match(r"!submit\s+\s+extension\s+(?P<assign_name>\w+)", message.content):
            return True

        return False

