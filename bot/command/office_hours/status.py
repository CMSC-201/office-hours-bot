import logging

from discord import Message, Client
from datetime import datetime, timedelta
import command
from globals import get_globals
from queues import QueueAuthority

logger = logging.getLogger(__name__)


@command.command_class
class QueueStatus(command.Command):
    __QUEUE_COLLECTION = 'queues'
    __MEMBER_ID_FIELD = "member-id"
    __REQUEST_FIELD = "request"
    __MESSAGE_ID_FIELD = "announcement"
    __REQUEST_TIME = 'request-time'

    def ordinal(self, num):
        suffixes = {1: 'st', 2: 'nd', 3: 'rd'}
        if 10 <= num % 100 <= 20:
            suffix = 'th'
        else:
            # the second parameter is a default.
            suffix = suffixes.get(num % 10, 'th')
        return str(num) + suffix

    def format_time(self, td: timedelta):
        s = td.seconds
        if s < 60:
            return '{} seconds'.format(s)
        elif s < 3600:
            return '{} minutes, {} seconds'.format(s//60, s % 60)
        else:
            return '{} hours, {} minutes, {} seconds'.format(s//3600, (s % 3600) // 60, s % 60)

    async def handle(self):
        qa: QueueAuthority = QueueAuthority(self.guild)
        queue = qa.retrieve_queue()

        found_student = False

        queue.sort(key=lambda x: x[self.__REQUEST_TIME])
        for i, student_data in enumerate(queue):
            if student_data[self.__MEMBER_ID_FIELD] == self.message.author.id:
                time_waited = datetime.now() - student_data[self.__REQUEST_TIME]
                await self.message.author.send('You are in the {} position and have been waiting for {}.'.format(self.ordinal(i + 1), self.format_time(time_waited)))
                found_student = True
        if not found_student:
            await self.message.author.send('You are not in the queue, use the !request <question> command to get in the queue')

        await self.message.delete(delay=3)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!status"):
            return True

        return False
