import logging
from discord import Message, Client, Guild
import command
from channels import ChannelAuthority

logger = logging.getLogger(__name__)


@command.command_class
class Which(command.Command):

    @command.Command.authenticate
    @command.Command.require_maintenance
    async def handle(self):
        channel_auth: ChannelAuthority = ChannelAuthority(self.guild)
        maintenance_channel = channel_auth.get_maintenance_channel()

        self.guild: Guild
        await maintenance_channel.send(f"{self.guild.name} has id {self.guild.id}")

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!which guild"):
            return True
        return False

