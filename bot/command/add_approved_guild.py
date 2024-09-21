import logging


from mongo import db
from discord import Message, Client, Guild
import command
import re
from channels import ChannelAuthority

logger = logging.getLogger(__name__)


@command.command_class
class AddApprovedGuild(command.Command):

    __APPROVED_GUILDS = 'approved-guilds'
    __GUILD_ID = 'guild-id'

    @command.Command.authenticate
    @command.Command.require_maintenance
    async def handle(self):
        channel_auth: ChannelAuthority = ChannelAuthority(self.guild)
        maintenance_channel = channel_auth.get_maintenance_channel()

        match = re.match(r'!add\s+approved\s+guild\s+(?P<guild_id>\.|\d+)', self.message.content)
        if not match:
            return

        guild_id = match.group('guild_id')
        if guild_id == '.':
            if db[self.__APPROVED_GUILDS].find_one({'guild-id': self.guild.id}):
                await maintenance_channel.send(f"{self.guild.name} with id {self.guild.id} is already in the approved list")
            else:
                db[self.__APPROVED_GUILDS].insert_one({'guild-id': self.guild.id, 'name': self.guild.name})
                await maintenance_channel.send(f"{self.guild.name} with id {self.guild.id} has been set to approved")
        else:  # set the guild id with the id specified to approved.
            try:
                guild_id = int(guild_id)
                db[self.__APPROVED_GUILDS].insert_one({'guild-id': guild_id, 'name': self.client.get_guild(guild_id).name})
            except ValueError:
                await maintenance_channel.send(f"The Guild ID must be an integer you entered {guild_id}")
                return


    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if re.match(r'!add\s+approved\s+guild\s+(?P<guild_id>\.|\d+)', message.content):
            return True
        return False

