from discord import Message, Client
from roles import RoleAuthority
import command


@command.command_class
class AmI(command.Command):
    async def handle(self, new_message=None):
        ra: RoleAuthority = RoleAuthority(self.guild)
        if self.message.content.strip().lower().startswith("!am i an admin"):
            if ra.is_admin(self.message.author):
                await self.message.channel.send('Yes you are an admin.')
            else:
                await self.message.channel.send('No you are not an admin.')
        elif self.message.content.strip().lower().startswith("!am i a ta"):
            if ra.is_ta(self.message.author):
                await self.message.channel.send('Yes you are a ta.')
            else:
                await self.message.channel.send('No you are not a ta.')
        elif self.message.content.strip().lower().startswith("!am i a student"):
            if ra.is_student(self.message.author):
                await self.message.channel.send('Yes you are a student.')
            else:
                await self.message.channel.send('No you are not a student.')

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return message.content.startswith("!am i")

    @classmethod
    def get_help(self):
        return 'This is a command which determines if you are an admin, ta, student, etc.'
