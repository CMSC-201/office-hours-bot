import re
from datetime import datetime, timedelta
from discord import Message, Client

from pymongo.results import InsertOneResult, UpdateResult, DeleteResult

import command
import mongo
from channels import ChannelAuthority
from roles import RoleAuthority


@command.command_class
class RemoveAssignment(command.Command):
    __COMMAND_REGEX = r"!submit\s+configure\s+(?P<assign_name>\w+)\s+remove"
    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'

    permissions = {'student': False, 'ta': False, 'admin': True}

    @command.Command.require_maintenance
    @command.Command.authenticate
    async def handle(self):
        match = re.match(self.__COMMAND_REGEX, self.message.content)
        assignments = mongo.db[self.__SUBMIT_ASSIGNMENTS]

        assignment_name = match.group('assign_name')
        dr: DeleteResult = assignments.delete_one({'name': assignment_name})
        if dr.deleted_count:
            await self.message.channel.send('Assignment {} has been removed'.format(assignment_name))
        else:
            await self.message.channel.send('Assignment {} has not been removed'.format(assignment_name))

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if re.match(r"!submit\s+configure\s+(?P<assign_name>\w+)\s+remove", message.content):
            return True
        return False
