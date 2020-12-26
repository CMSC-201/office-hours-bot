import logging

from discord import Message, Client, Member, Guild

import command
from channels import ChannelAuthority
from queues import QueueAuthority, OHSession
from roles import RoleAuthority

logger = logging.getLogger(__name__)


@command.command_class
class RejectStudent(command.Command):

    permissions = {'student': False, 'ta': True, 'admin': True}

    @command.Command.authenticate
    async def handle(self):
        qa: QueueAuthority = QueueAuthority(self.guild)

        student_id = self.message.content.split(" ")[1]
        student: Member = await self.guild.fetch_member(int(student_id))

        session: OHSession = await qa.find_and_remove_by_user_id(student)
        await session.announcement.delete()
        reject_message = " ".join(self.message.content.split(" ")[2:])
        await student.send("You have been removed from the office hour queue, because: {}".format(reject_message))

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):

        if message.content.startswith("!reject"):
            ra: RoleAuthority = RoleAuthority(message.guild)

            # check if the sender has permission to issue this command
            if ra.ta_or_higher(message.author):
                ca: ChannelAuthority = ChannelAuthority(message.guild)
                malformed = False

                # Check to see if a there is a valid member id and message
                guild: Guild = message.guild
                try:
                    # checks for at least 3 words
                    if len(message.content.split(" ")) < 3:
                        malformed = True
                    else:
                        member_id = int(message.content.split(" ")[1])
                        member_mentioned: Member = await guild.fetch_member(member_id)
                        # checks if the supplied id is a valid id
                        if not member_mentioned:
                            malformed = True
                # if an exception is thrown above, then it's something real wonkey (like a non-int id)
                except:
                    malformed = True

                # tell them it's malformed and supply correct format
                if malformed:
                    admonishment = await message.channel.send(
                        "Reject must be of the form `!reject [integer userid] [message]`".format(
                            message.author.mention,
                            ca.queue_channel.mention
                        ))
                    await admonishment.delete(delay=7)
                    await message.delete()
                    return False
                # if it's well-formed and in the correct channel, we have success!
                if message.channel == ca.queue_channel:
                    return True
                else:
                    # else point them to the correct channel
                    admonishment = await message.channel.send("{}, you must be in {} to reject a student.".format(
                        message.author.mention,
                        ca.queue_channel.mention
                    ))
                    await admonishment.delete(delay=7)
                    await message.delete()
                    return False
            else:
                admonishment = await message.channel.send("Silly {}, you're not a TA!".format(
                    message.author.mention
                ))
                await admonishment.delete(delay=7)
                await message.delete()
                return False

        return False
