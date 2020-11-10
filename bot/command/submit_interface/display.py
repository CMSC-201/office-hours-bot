import re
from datetime import datetime, timedelta
from discord import Message, Client, Embed, Colour

from pymongo.results import InsertOneResult, UpdateResult

import command
import mongo
from channels import ChannelAuthority
from roles import RoleAuthority


@command.command_class
class ConfigureAssignment(command.Command):
    __SUBMIT_SYSTEM_ADMINS = 'submit-system-admins'
    __SUBMIT_ASSIGNMENTS = 'submit-assignments'

    __STUDENT_EXT = 'student-extensions'
    __SECTION_EXT = 'section-extensions'
    __ASSIGNMENT_NAME = 'name'
    __MONGO_ID = "_id"

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

    async def handle(self):
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        ra: RoleAuthority = RoleAuthority(self.guild)
        if ra.is_admin(self.message.author) and ca.is_maintenance_channel(self.message.channel):
            assignments = mongo.db[self.__SUBMIT_ASSIGNMENTS]
            lines = []
            for assignment in assignments.find():
                for attr in assignment:
                    if isinstance(assignment[attr], datetime):
                        lines.append("{}: {}".format(attr, assignment[attr].strftime('%Y-%m-%d %H:%M:%S')))
                    elif isinstance(assignment[attr], dict):
                        lines.append("{}:".format(attr))
                        for subattr in assignment[attr]:
                            if isinstance(assignment[attr][subattr], dict):
                                for subsubattr in assignment[attr][subattr]:
                                    if isinstance(assignment[attr][subattr][subsubattr], datetime):
                                        lines.append("\t{}: {}".format(subsubattr, assignment[attr][subattr][subsubattr].strftime('%Y-%m-%d %H:%M:%S')))
                                    else:
                                        lines.append("\t{}: {}".format(subsubattr, assignment[attr][subattr][subsubattr]))
                            elif isinstance(assignment[attr][subattr], datetime):
                                lines.append("\t{}: {} {}".format(subattr, assignment[attr][subattr].strftime('%Y-%m-%d %H:%M:%S'), type(assignment[attr][subattr])))
                            else:
                                lines.append("\t{}: {} {}".format(subattr, assignment[attr][subattr], type(assignment[attr][subattr])))
                    else:
                        lines.append("{}: {}".format(attr, assignment[attr]))

                embedded_message = Embed(description='\n'.join(lines), timestamp=datetime.now() + timedelta(hours=4), colour=Colour(0).teal())
                total_string = '\t'.join([':'.join([key, str(assignment[key])]) for key in assignment])
                for i in range(0, len(total_string) // 1000 + 1, 1000):
                    await self.message.channel.send(total_string[i: i + 1000])
                # await self.message.channel.send(embed=embedded_message)
                embedded_message = Embed(description=self.format_assignment(assignment))
                # await self.message.channel.send(embed=embedded_message)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if re.match(r"!submit\s+display\s+assignments", message.content):
            return True
        return False
