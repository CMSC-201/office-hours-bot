import logging

from discord import Message, Client

import command
from globals import get_globals
from queues import QueueAuthority

logger = logging.getLogger(__name__)


@command.command_class
class QueueStatus(command.Command):
    async def handle(self):
        qa: QueueAuthority = QueueAuthority(self.guild)
        queue = qa.retrieve_queue()
        if "id" in self.message.content:
            await self.message.author.send("Your id is {}.  Your spot in the queue will appear here: {}".format(
                self.message.author.id,
                get_globals()["props"]["queue_url"],
            ))

        else:
            msg: Message = await self.message.channel.send(
                "Queue status can be viewed here:  {}.  Do `!status id` and I will DM you your id.".format(
                    get_globals()["props"]["queue_url"]
                ))
            await msg.delete(delay=10)

        await self.message.delete()

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!status"):
            return True

        return False
