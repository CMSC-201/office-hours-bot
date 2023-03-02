import logging
import datetime as dt

from discord import Guild, Message, Client, Member, User, Embed, Colour, TextChannel, VoiceChannel, CategoryChannel

import command
import mongo
from channels import ChannelAuthority

logger = logging.getLogger(__name__)


@command.command_class
class DisplayChannels(command.Command):
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'TA'
    __STUDENTS_GROUP = 'student'
    __UID_FIELD = 'UMBC-Name-Id'
    __DISCORD_ID = 'discord'
    __ROLE = 'Role'
    __FIRST_NAME = 'First-Name'
    __LAST_NAME = 'Last-Name'

    permissions = {'student': False, 'ta': False, 'admin': True}

    @command.Command.authenticate
    async def handle(self):
        try:
            channel_authority: ChannelAuthority = ChannelAuthority(self.guild)
            maintenance_channel = channel_authority.get_maintenance_channel()
            waiting_channel = channel_authority.waiting_channel.id
            queue_channel = channel_authority.queue_channel.id
            message_text = f'{maintenance_channel.name}\t{maintenance_channel.id}\n'
            message_text += f'{waiting_channel.name}\t{waiting_channel.id}\n'
            message_text += f'{queue_channel.name}\t{queue_channel.id}\n'
            embedded_message = Embed(title=f"Primary Channels", description=message_text, timestamp=dt.datetime.now(), colour=Colour(0).teal())
            await self.message.channel.send(embed=embedded_message)
        except ReferenceError as ref_error:
            await self.message.channel.send(f"Unable to load channels from database.  {ref_error}")

        if '-all' in self.message.content:
            self.guild: Guild
            for category in self.guild.categories:
                message_text = f'{category.name}\tid={category.id}\n'
                for channel in category.text_channels:
                    message_text += f"{channel.name}\tid = {channel.id}\tguild = {channel.guild.id}\n"
                embedded_message = Embed(title=f"{category.name}", description=message_text, timestamp=dt.datetime.now(), colour=Colour(0).teal())
                await self.message.channel.send(embed=embedded_message)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!display channels"):
            return True

        return False
