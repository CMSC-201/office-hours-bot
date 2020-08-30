import logging
from discord import Message, Client, Member

import command
from channels import ChannelAuthority
from queues import QueueAuthority

logger = logging.getLogger(__name__)

@command.command_class
class Who(command.Command):
    async def handle(self):
        qa: QueueAuthority = QueueAuthority(self.guild)

        tas = qa.on_duty_ta_list()
        msg_indentor = "\n  * "
        ret_msg = "TAs on duty:" + msg_indentor

        # Use the typing indocator just for pizzazz
        #async with self.message.channel.typing():
        await self.message.channel.trigger_typing()

        # Prepare message
        if not tas:
            ret_msg = "There are no TAs currently on duty."
        else:
            #ta_names = [self.client.get_user(uid).display_name for uid in tas]
            ta_names = [self.guild.get_member(uid).nick for uid in tas]
            ret_msg += msg_indentor.join(ta_names)

        msg = await self.message.channel.send(ret_msg)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!who"):
            ca: ChannelAuthority = ChannelAuthority(message.guild)
            qa: QueueAuthority = QueueAuthority(message.guild)

            if not qa.is_office_hours_open():
                warning = await message.channel.send(
                    "Office hours are closed.  Please try again after they have opened.".format(
                        message.author.mention,
                        ca.waiting_channel.mention))
                await warning.delete(delay=7)
                await message.delete(delay=1)

                return False

            return True
        return False
