from discord import Message, Client, Member
import discord
import command
import mongo
import re
from datetime import datetime, timedelta


@command.command_class
class GetRegisteredLectures(command.Command):
    __LECTURE_ATTENDANCE = 'lecture-attendance'
    __LECTURE_ATTENDANCE_SECTIONS = 'lecture-attendance-sections'
    __KEY_TYPE = 'key-type'
    __SECTION_LIST = 'section-list'
    __DAY_LIST = 'day-list'
    __MONGO_ID = '_id'

    __COMMAND_REGEX = r'!attendance\s+get\s+registered\s+lectures'

    permissions = {'student': False, 'ta': False, 'admin': True}

    @command.Command.authenticate
    @command.Command.require_maintenance
    async def handle(self, new_message=None):
        regex_match = re.match(self.__COMMAND_REGEX, self.message.content)
        if not regex_match:
            await self.safe_send(self.message.channel, 'Unable to create the new lecture attendance section.  Invalid command format. \nShould be !attendance register lecture [lec_name] sections = 11, 12, 13, 14, 15, 16')
            return False

        lecture_attendance_sections_db = mongo.db[self.__LECTURE_ATTENDANCE_SECTIONS]
        sections = lecture_attendance_sections_db.find_one({self.__KEY_TYPE: self.__SECTION_LIST})

        print(sections)
        color = discord.Colour(0).blue()
        embeddedMsg = discord.Embed(description='Lecture Sections for Attendance', timestamp=datetime.now() + timedelta(hours=5), colour=color)
        author: Member = self.message.author
        embeddedMsg.set_author(name=command.name(author))
        for section_name in sections:
            if section_name not in [self.__KEY_TYPE, self.__MONGO_ID]:
                embeddedMsg.add_field(name=section_name, value=', '.join([str(x) for x in sections[section_name]]))

        await self.message.channel.send(embed=embeddedMsg)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        __COMMAND_REGEX = r'!attendance\s+get\s+registered\s+lectures'
        if re.match(__COMMAND_REGEX, message.content):
            return True
        return False

    @classmethod
    def get_help(self):
        return 'This command will register a set of sections as a lecture for the purposes of attendance. '
