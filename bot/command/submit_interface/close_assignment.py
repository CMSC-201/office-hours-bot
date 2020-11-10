__DOCSTRING__ = """
    Totally non-functional.
"""

import re
from datetime import datetime, timedelta
from discord import Message, Client

from pymongo.results import InsertOneResult, UpdateResult, DeleteResult

import command
import mongo
from channels import ChannelAuthority
from roles import RoleAuthority


@command.command_class
class CloseAssignment(command.Command):
    __COMMAND_REGEX = r"!submit\s+configure\s+(?P<assign_name>\w+)\s+remove(\s+(?P<admin>--admin=\w+))?"
    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'

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

            # re close the assignment.

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if re.match(r"!submit\s+close\s+(?P<assign_name>\w+)(\s+(?P<admin>--admin=\w+))?", message.content):
            return True
        return False