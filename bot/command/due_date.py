import logging
import re

from datetime import datetime
from discord import Message, Client, Member, Guild

import command
import mongo
from roles import RoleAuthority

logger = logging.getLogger(__name__)


@command.command_class
class DueDate(command.Command):
    __ASSIGNMENTS = 'assignments'
    __ASSIGN_NAME = 'name'
    __DB_ID = '_id'
    __DUE_DATE = 'due-date'

    async def handle(self):
        assignments_db = mongo.db[self.__ASSIGNMENTS]
        sender: Member = self.message.author
        ra: RoleAuthority = RoleAuthority(self.guild)

        set_match = re.match(r'!due\s+date\s+set\s+(?P<assignment_name>\w+)\s+(?P<date_and_time>\d{2}-\d{2}-\d{4}\s+\d{2}:\d{2}:\d{2})', self.message.content)
        get_match = re.match(r'!due\s+date\s+(?P<assignment_name>\w+)', self.message.content)

        response_message = 'Unable to process your command, bad format.  '

        if ra.is_admin(sender) and set_match:
            assignment_match = assignments_db.find_one({self.__ASSIGN_NAME: get_match.group('assignment_name')})
            # rejoin with only one space for datetime formatting
            date_string = ' '.join(set_match.group('date_and_time').split())
            new_time = datetime.strptime(date_string, '%m-%d-%Y %H:%M:%S')
            if assignment_match:
                assignments_db.update_one({self.__DB_ID: assignment_match[self.__DB_ID]}, {'$set': {self.__DUE_DATE: new_time}}, upsert=True)
            else:
                assignment_match = {self.__ASSIGN_NAME: set_match.group('assignment_name'), self.__DUE_DATE: new_time}
                assignments_db.insert_one(assignment_match)
            response_message = 'The Due Date for {} is now set to {}'.format(assignment_match[self.__ASSIGN_NAME],
                                                                             assignment_match[self.__DUE_DATE].strftime('%m-%d-%Y %H:%M:%S'))
        elif get_match:
            assignment_match = assignments_db.find_one({self.__ASSIGN_NAME: get_match.group('assignment_name')})
            response_message = 'The Due Date for {} is {}'.format(assignment_match[self.__ASSIGN_NAME],
                                                                  assignment_match[self.__DUE_DATE].strftime('%m-%d-%Y %H:%M:%S'))

        if self.message.guild:
            await self.message.channel.send(response_message)
        else:
            await self.message.author.send(response_message)

    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!due date"):
            return True
        return False

    async def is_invoked_by_direct_message(message: Message, client: Client, guild: Guild):
        if message.content.startswith("!due date"):
            return True
        return False
