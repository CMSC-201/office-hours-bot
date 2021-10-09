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
    __ASSIGNMENTS = 'submit-assignments'
    __ASSIGN_NAME = 'name'
    __DB_ID = '_id'
    __DUE_DATE = 'due-date'
    __STUDENTS_GROUP = 'student'
    __USERNAME = 'UMBC-Name-Id'
    __DISCORD_ID = 'discord'
    __SECTION = 'Section'

    async def handle(self):
        assignments_db = mongo.db[self.__ASSIGNMENTS]
        students_group = mongo.db[self.__STUDENTS_GROUP]

        sender: Member = self.message.author
        get_match = re.match(r'!due\s+date\s+(?P<assignment_name>\w+)', self.message.content)

        response_message = 'Unable to process your command, bad format.  '

        # self.message.guild checks to ensure it isn't a DM, you must set/rem assignments from a channel within the guild
        # users can query using their DM-ing skills with the Bot.

        assignment_match = None
        if get_match:
            assignment_match = assignments_db.find_one({self.__ASSIGN_NAME: get_match.group('assignment_name')})
            if assignment_match:
                student = students_group.find_one({self.__DISCORD_ID: sender.id})
                if student and student[self.__SECTION] in assignment_match['section-extensions']:
                    response_message = 'The original due date for {} is {}, but your extension gives you until {}' \
                        .format(assignment_match[self.__ASSIGN_NAME],
                                assignment_match[self.__DUE_DATE].strftime('%m-%d-%Y %H:%M:%S'),
                                assignment_match['section-extensions'][self.__DUE_DATE].strftime('%m-%d-%Y %H:%M:%S'))
                elif student and student[self.__USERNAME] in assignment_match['student-extensions']:
                    response_message = 'The original due date for {} is {}, but your extension gives you until {}' \
                        .format(assignment_match[self.__ASSIGN_NAME],
                                assignment_match[self.__DUE_DATE].strftime('%m-%d-%Y %H:%M:%S'),
                                assignment_match['student-extensions'][student[self.__USERNAME]][self.__DUE_DATE].strftime('%m-%d-%Y %H:%M:%S'))
                else:
                    response_message = 'The Due Date for {} is {}'.format(assignment_match[self.__ASSIGN_NAME],
                                                                          assignment_match[self.__DUE_DATE].strftime('%m-%d-%Y %H:%M:%S'))
        if not get_match or not assignment_match:
            response_message = 'I was unable to find which assignment you were looking for.  Options are:\n\t' \
                               + ', '.join([am[self.__ASSIGN_NAME] for am in assignments_db.find({})])

        if self.message.guild:
            await self.message.channel.send(response_message)
        else:
            await self.message.author.send(response_message)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!due date"):
            return True
        return False

    @staticmethod
    async def is_invoked_by_direct_message(message: Message, client: Client):
        if message.content.startswith("!due date"):
            return True
        return False

    @classmethod
    def get_help(cls):
        import textwrap
        return textwrap.dedent(
            """Get the due date of an assignment by its name.  If no name is specified, it will output all of the assignments in the database.  
            Command Format: !due date <assignment name>""")
