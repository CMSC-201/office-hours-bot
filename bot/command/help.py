import logging

from discord import Message, Client, Member

import command
from roles import RoleAuthority

logger = logging.getLogger(__name__)


@command.command_class
class Help(command.Command):
    prefix = "https://github.com/CMSC-201/office-hours-bot/blob/master/"

    async def handle(self):
        sender: Member = self.message.author
        ra: RoleAuthority = RoleAuthority(self.guild)
        if ra.ta_or_higher(sender):
            await self.message.channel.send("{}, great and powerful course staff member! "
                                            "Go to {} to see all the ways I may serve you!".format(
                sender.mention, self.prefix + "tahelp.md"
            ))
        else:
            await self.message.channel.send("You can find a guide to using office hours here: {}".format(
                self.prefix + "student.md"
            ))

    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!help"):
            return True
        return False
