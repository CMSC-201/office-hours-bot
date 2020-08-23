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
        member: Member = self.guild.get_member(self.message.author.id)

        await self.message.author.send('Starting your authentication process...')
        if await ma.authenticate_member(member, key):
            logger.info("Authenticated user {0.display_name} ({0.id}) as {0.nick}".format(member))
            await self.message.author.send('''You are now authenticated!  You can return to the office hour server.\n  
                                I live here so I won't actually be going anywhere, but you don't have to talk to me anymore.''')
        else:
            await self.message.author.send("Key unrecognized.  Please try again.  " +
                                                      "If you're still having trouble, please contact course staff.")

    @staticmethod
    async def is_invoked_by_direct_message(message: Message, client: Client):
        if message.content.startswith("!auth resend"):
            await message.author.send('Welcome to Discord Office Hours for CMSC 201, Fall 2020\n I am the 201Bot.' +
                                      '\n  Send me a message with !auth (your key pasted here), and we\'ll authenticate you on the channel.')
            return False
        if message.content.startswith("!auth"):
            if len(message.content.split()) != 2:
                warning = await message.author.send("Please try again.  The format is !auth [your key]")
                await warning.delete(delay=7)
                return False

            return True

        return False

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!auth resend"):
            await message.author.send('Welcome to Discord Office Hours for CMSC 201, Fall 2020\n I am the 201Bot.\n  Send me a message with !auth (your key pasted here), and we\'ll authenticate you on the channel.')
        elif message.content.startswith("!auth") and message.guild:
            await message.author.send("Don't share your key via any channel, only send it to me, the discord bot in a DM!")
        return False
