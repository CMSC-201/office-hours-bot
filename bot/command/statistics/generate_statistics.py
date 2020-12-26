import logging

from datetime import datetime, timedelta
from discord import Message, Client, TextChannel, CategoryChannel, PermissionOverwrite, Role
from discord.errors import NotFound

import csv
import command
from channels import ChannelAuthority
from roles import RoleAuthority

logger = logging.getLogger(__name__)


@command.command_class
class GenerateStatistics(command.Command):

    async def handle(self):
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        ra: RoleAuthority = RoleAuthority(self.guild)

        student_comments = {}
        ta_comments = {}
        professor_comments = {}

        member_dictionary = {}

        if ra.ta_or_higher(self.message.author) and ca.is_maintenance_channel(self.message.channel):
            for category in self.guild.categories:
                if category.name == 'Course Rooms':
                    for channel in category.text_channels:
                        if channel.name == 'on-topic':
                            await self.message.channel.send('The on topic channel was found. ')
                            previous_day = datetime(year=2020, month=8, day=31)
                            current_day = previous_day + timedelta(days=1)
                            while current_day < datetime.now():
                                print(previous_day, current_day)
                                student_comments[previous_day] = 0
                                ta_comments[previous_day] = 0
                                professor_comments[previous_day] = 0

                                async for message in channel.history(limit=None, before=current_day, after=previous_day):
                                    try:
                                        message: Message
                                        if message.author.id in member_dictionary:
                                            member = member_dictionary[message.author.id]
                                        else:
                                            member = await self.guild.fetch_member(message.author.id)
                                            member_dictionary[message.author.id] = member

                                        if ra.is_admin(member):
                                            professor_comments[previous_day] += 1
                                        elif ra.ta_or_higher(member):
                                            ta_comments[previous_day] += 1
                                        else:
                                            student_comments[previous_day] += 1
                                    except NotFound:
                                        pass
                                print(previous_day, student_comments[previous_day], ta_comments[previous_day], professor_comments[previous_day], sep='\t')
                                await self.safe_send(self.message.channel, '\t'.join([previous_day.strftime('%Y-%m-%d'),  str(student_comments[previous_day]), str(ta_comments[previous_day]), str(professor_comments[previous_day])]))
                                previous_day = current_day
                                current_day = previous_day + timedelta(days=1)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith('!generate statistics'):
            return True

        return False
