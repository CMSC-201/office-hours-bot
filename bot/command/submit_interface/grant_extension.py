import re
from discord import Message, Client

from pymongo.results import InsertOneResult, UpdateResult

import command
import mongo
import json
from channels import ChannelAuthority
from roles import RoleAuthority


@command.command_class
class GrantExtension(command.Command):
    __COMMAND_REGEX = r"!submit\s+(grant|give)\s+extension\s+(?P<assign_name>\w+)\s+((section\s+=(?P<section_id>\w+)|(student\s+=(?P<student_id>\w+))\s+(?P<due_date>\d{2}-\d{2}-\d{4})\s+(?P<due_time>\d{2}:\d{2}:\d{2})(\s+--admin=(?P<admin>\w+))?"
    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'

    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'
    __UID_FIELD = 'UMBC-Name-Id'

    async def handle(self):
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        ra: RoleAuthority = RoleAuthority(self.guild)
        if ra.is_admin(self.message.author) and ca.is_maintenance_channel(self.message.channel):
            match = re.match(self.__COMMAND_REGEX, self.message.content)
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

            if assignment and section_id:
                pass
            elif assignment and student_id:
                pass

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!submit grant extension"):
            return True
        return False
