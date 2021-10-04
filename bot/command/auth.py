import logging

from discord import Message, Client, Member, TextChannel, CategoryChannel, PermissionOverwrite, Role, Permissions

import globals
import command
from member import MemberAuthority

logger = logging.getLogger(__name__)


@command.command_class
class AuthenticateStudent(command.Command):
    async def handle(self):
        ma: MemberAuthority = MemberAuthority(self.guild)

        key = self.message.content.split()[1]
        # fetch to start the auth process.
        await self.message.author.send('Starting your authentication process...')
        member: Member = await self.guild.fetch_member(self.message.author.id)
        result = await ma.authenticate_member(member, key)
        # fetch again to get the nickname
        member: Member = await self.guild.fetch_member(self.message.author.id)
        if result == MemberAuthority.AUTHENTICATED:
            logger.info("Authenticated user {0.display_name} ({0.id}) as {0.nick}".format(member))
            await self.message.author.send('''You are now authenticated!  You can return to the office hour server.\n  
                                I live here so I won't actually be going anywhere, but you don't have to talk to me anymore.''')
        elif result == MemberAuthority.SAME_ACCOUNT:
            await self.message.author.send("This account has already been authenticated, go to the discord server for your class and you should see the rooms.")
        elif result == MemberAuthority.DUPLICATE_ACCOUNT:
            await self.message.author.send("This key has already been used to authenticate, and is no longer valid.\n\tIf you want to use a different account, contact course staff and tell them that you have already authenticated and want to switch accounts.")
        elif result == MemberAuthority.UNABLE_TO_UPDATE:
            await self.message.author.send("There was an internal database error, unable to update with new discord id.  Try again. ")
        else:
            await self.message.author.send("There is no user account associated with this key.\n\tTry again, make sure to copy and paste the key with !auth.\n\tIf you're still having trouble, please contact course staff.")
        if self.message.guild:
            await self.message.delete()

    @staticmethod
    async def is_invoked_by_direct_message(message: Message, client: Client):
        class_name = globals.get_globals()['props'].get('class_name', 'CMSC 201')
        bot_name = globals.get_globals()['props'].get('class_name', '201Bot')
        if message.content.startswith("!auth resend"):
            await message.author.send('Welcome to Discord Office Hours for {}}\n I am the {}}.'.format(class_name, bot_name) +
                                      '\n  Send me a message with !auth (your key pasted here), and we\'ll authenticate you on the channel.')
            return False
        if message.content.startswith("!auth"):
            if len(message.content.split()) != 2:
                warning = await message.author.send("Please try again.  The format is !auth [your key]")
                if message.guild:
                    await warning.delete(delay=7)
                return False

            return True

        return False

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        class_name = globals.get_globals()['props'].get('class_name', 'CMSC 201')
        bot_name = globals.get_globals()['props'].get('class_name', '201Bot')
        if message.content.startswith("!auth resend"):
            await message.author.send('Welcome to Discord Office Hours for {}\n I am the {}.\n  Send me a message with !auth (your key pasted here), and we\'ll authenticate you on the channel.'.format(class_name, bot_name))
        elif message.content.startswith("!auth"):
            await message.author.send("Don't share your key via any channel, only send it to me, the discord bot in a DM!")
            await message.delete(delay=5)
        return False
