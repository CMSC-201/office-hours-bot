import logging

from discord import Message, Client, Member, TextChannel, CategoryChannel, PermissionOverwrite, Role, Permissions

import command
from channels import ChannelAuthority
from member import MemberAuthority
from roles import RoleAuthority

logger = logging.getLogger(__name__)

@command.command_class
class AuthenticateStudent(command.Command):
    async def handle(self):
        ma: MemberAuthority = MemberAuthority(self.guild)
        key = self.message.content.split()[1]
        member: Member = self.message.author
        if await ma.authenticate_member(member, key):
            logger.info("Authenticated user {0.display_name} ({0.id}) as {0.nick}".format(self.message.author))
        else:
            warning = await self.message.channel.send("Key unrecognized.  Please try again.  " + \
                                                      "If you're still having trouble, please contact course staff.")
            await warning.delete(delay=7)

        await self.message.delete()

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        ca: ChannelAuthority = ChannelAuthority(message.guild)
        if message.content.startswith("!auth"):
            if len(message.content.split()) != 2:
                warning = await message.author.send("Please try again.  The format is !auth [your key]")
                await warning.delete(delay=7)
            elif message.channel == ca.auth_channel:
                return True
            else:
                warning = await message.channel.send("You have to be in {} to authenticate.".format(
                    ca.auth_channel.mention))
                await warning.delete(delay=7)
        return False
