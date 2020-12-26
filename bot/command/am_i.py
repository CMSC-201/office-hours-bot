from discord import Message, Client
from roles import RoleAuthority
import command

@command.command_class
class AmI(command.Command):
    async def handle(self, new_message=None):
        ra: RoleAuthority = RoleAuthority(self.guild)
        if self.message.content.strip().startswith("!am i an admin"):
            if ra.is_admin(self.message.author):
                await self.message.channel.send('Yes you are an admin.')
            else:
                await self.message.channel.send('No you are not an admin.')

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return message.content.startswith("!am i")

    @classmethod
    def get_help(self):
        return 'This is a command which determines if you are an admin, ta, student, etc.'
