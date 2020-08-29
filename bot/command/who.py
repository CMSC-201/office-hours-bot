from discord import Message, Client

import command
from queues import QueueAuthority


@command.command_class
class Bark(command.Command):
    async def handle(self):
        qa: QueueAuthority = QueueAuthority(self.guild)

        tas = qa.on_duty_ta_list()
        msg_indentor = "\n  * "
        ret_msg = "TAs on duty:" + msg_indentor

        # Use the typing indocator just for pizzazz
        async with self.message.channel.typing():
			# Prepare message
            if not tas:
                ret_msg = "There are no TAs currently on duty."
            else:
                ta_names = [self.client.get_user(uid).display_name for uid in tas]
                ret_msg += msg_indentor.join(ta_names)

            msg = await self.message.channel.send(ret_msg)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return message.content.startswith("!who")
