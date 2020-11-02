import logging

from discord import Message, Client, TextChannel, CategoryChannel, PermissionOverwrite, Role
from discord.errors import NotFound

import command
from channels import ChannelAuthority
from queues import QueueAuthority, OHSession
from roles import RoleAuthority

logger = logging.getLogger(__name__)


@command.command_class
class AcceptStudent(command.Command):
    async def handle(self):
        qa: QueueAuthority = QueueAuthority(self.guild)
        if not qa.is_ta_on_duty(self.message.author.id):
            await self.message.channel.send("You must be on duty to accept a request!")
            return
        # get oldest queue item (and also remove it)
        session: OHSession = await qa.dequeue(self.message.author)
        if not session:
            msg = await self.message.channel.send("No one is in the queue.  Perhaps you're lonely?\n"
                                                  "https://giphy.com/gifs/30-rock-liz-lemon-jack-donaghy-VuWtVHkMjrz2w")
            await msg.delete(delay=7)
            await self.message.delete()
            return
        # create role for channel
        role: Role = await self.guild.create_role(name="{}'s OH session".format(command.name(session.member)), hoist=True)
        num_roles = len(self.guild.roles)
        # todo find bot role insert this underneath
        # await role.edit(position=num_roles-2)
        session.role = role
        await session.member.add_roles(session.role)
        await self.message.author.add_roles(session.role)

        # create channel
        ra: RoleAuthority = RoleAuthority(self.guild)
        session_category: CategoryChannel = await self.guild.create_category_channel(
            "Session for {}".format(command.name(session.member)),
            overwrites={
                role: PermissionOverwrite(read_messages=True, attach_files=True, embed_links=True),
                ra.student: PermissionOverwrite(read_messages=False),
                ra.un_authenticated: PermissionOverwrite(read_messages=False)
            })
        text_channel: TextChannel = await session_category.create_text_channel("Text Cat")
        await session_category.create_voice_channel("Voice chat")
        session.room = session_category
        # attach user ids and channel ids to OH room info in channel authority
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        await session.announcement.delete()

        ca.add_oh_session(session)
        await text_channel.send("Hi, {} and {}!  Let the learning commence!  Type !close to end the session!".format(
            session.member.mention,
            session.ta.mention,
        ))
        await text_channel.send('The question asked/help requested was: {}'.format(session.request))
        logger.info("OH session for {} accepted by {}".format(
            command.name(session.member),
            command.name(self.message.author)))

        try:
            await self.message.delete()
        except NotFound:
            await self.message.channel.send('Deleting the accept message can potentially cause errors, allow me to delete it for you.')

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):

        if message.content.startswith("!accept"):
            ra: RoleAuthority = RoleAuthority(message.guild)
            if ra.ta_or_higher(message.author):
                ca: ChannelAuthority = ChannelAuthority(message.guild)
                if message.channel == ca.queue_channel:
                    return True
                else:
                    admonishment = await message.channel.send("{}, you must be in {} to accept a student.".format(
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
