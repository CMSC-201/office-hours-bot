import re
from datetime import datetime, timedelta
from discord import Message, Client, Embed, Colour

import command
import mongo


@command.command_class
class DisplayAssignment(command.Command):
    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'

    __STUDENT_EXT = 'student-extensions'
    __SECTION_EXT = 'section-extensions'
    __ASSIGNMENT_NAME = 'name'
    __DUE_DATE = 'due-date'
    __OPEN = 'open'

    __MONGO_ID = "_id"
    permissions = {'student': False, 'ta': True, 'admin': True}

    def format_assignment(self, assignment):
        assignment_lines = []

        for key in assignment:
            if isinstance(assignment[key], datetime):
                assignment_lines.append("{}: {}".format(key.capitalize(), assignment[key].strftime('%Y-%m-%d %H:%M:%S')))
            elif isinstance(assignment[key], dict):
                pass
            else:
                assignment_lines.append("{}: {}".format(key.capitalize(), assignment[key]))

        return '\n'.join(assignment_lines)

    @command.Command.authenticate
    @command.Command.require_maintenance
    async def handle(self):
        assignments = mongo.db[self.__SUBMIT_ASSIGNMENTS]

        if self.message.content.startswith('!submit display assignments'):
            printable_string = ''
            assignment_embed = Embed(description="", timestamp=datetime.now() + timedelta(hours=4), colour=Colour(0).teal())
            for assignment in assignments.find():

                printable_string += '\n\n' + "\n\t".join([assignment[self.__ASSIGNMENT_NAME], 'Due Date: {}'.format(assignment[self.__DUE_DATE].strftime('%Y-%m-%d %H:%M:%S')), 'Open: {}'.format(str(assignment[self.__OPEN]))])
                assignment_embed = Embed(description=printable_string, timestamp=datetime.now() + timedelta(hours=4), colour=Colour(0).teal())
                if len(printable_string) >= 1000:
                    await self.message.channel.send(embed=assignment_embed)
                    printable_string = ''

            await self.message.channel.send(embed=assignment_embed)
        elif re.match(r'!submit\s+display\s+assignment\s+(?P<assignment_name>\w+)', self.message.content):
            match_result = re.match(r'!submit\s+display\s+assignment\s+(?P<assignment_name>\w+)', self.message.content)
            assignment_name = match_result.group('assignment_name')

            for assignment in assignments.find():
                if assignment[self.__ASSIGNMENT_NAME].lower() == assignment_name.lower().strip():
                    print(assignment)
                    printable_string = "\n\t".join([assignment[self.__ASSIGNMENT_NAME], 'Due Date: {}'.format(assignment[self.__DUE_DATE].strftime('%Y-%m-%d %H:%M:%S')), 'Open: {}'.format(str(assignment[self.__OPEN]))])
                    if assignment[self.__STUDENT_EXT]:
                        for student in assignment[self.__STUDENT_EXT]:
                            printable_string += "\nStudent: {}\tDue Date: {}\t Open: {}".format(student, assignment[self.__STUDENT_EXT][student][self.__DUE_DATE].strftime('%Y-%m-%d %H:%M:%S'), assignment[self.__STUDENT_EXT][student][self.__OPEN])
                    assignment_embed = Embed(description=printable_string, timestamp=datetime.now() + timedelta(hours=4), colour=Colour(0).teal())
                    await self.message.channel.send(embed=assignment_embed)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if re.match(r"!submit\s+display\s+assignment(s|\s+\w+)", message.content):
            return True
        return False
