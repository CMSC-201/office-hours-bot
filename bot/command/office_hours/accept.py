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
    __MEMBER_ID_FIELD = "member-id"
    __REQUEST_TIME = 'request-time'

    permissions = {'student': False, 'ta': True, 'admin': True}

    @command.Command.authenticate
    async def handle(self):
        debug_mode = False
        if '--debug' in self.message.content:
            debug_mode = True
            await self.message.channel.send('accepted session, debug enabled')

        qa: QueueAuthority = QueueAuthority(self.guild)
        if not qa.is_ta_on_duty(self.message.author.id):
            await self.message.channel.send("You must be on duty to accept a request!")
            return
        # get oldest queue item (and also remove it)
        session: OHSession = await qa.dequeue(self.message.author)
        if debug_mode:
            await self.message.channel.send(f"accept request dequeued {self.message.author.nick}, {self.message.author.id}")
        if not session:
            msg = await self.message.channel.send("No one is in the queue.  Perhaps you're lonely?\n"
                                                  "https://giphy.com/gifs/30-rock-liz-lemon-jack-donaghy-VuWtVHkMjrz2w")
            await msg.delete(delay=7)
            await self.message.delete()
            return

        ra: RoleAuthority = RoleAuthority(self.guild)

        if session.member:
            role = None
            while not role:
                try:
                    role: Role = await self.guild.create_role(name=f"{command.name(session.member)}'s OH session", hoist=True)

                    session.role = role
                    await session.member.add_roles(session.role)
                    await self.message.author.add_roles(session.role)
                except NotFound:
                    await self.message.channel.send('Unable to create the OH session role.')

            session_category: CategoryChannel = await self.guild.create_category_channel(
                f"Session for {command.name(session.member)}",
                overwrites={
                    role: PermissionOverwrite(read_messages=True, attach_files=True, embed_links=True),
                    ra.get_student_role(): PermissionOverwrite(read_messages=False),
                    ra.get_unauthenticated_role(): PermissionOverwrite(read_messages=False)
                })
            text_channel: TextChannel = await session_category.create_text_channel("Text Chat")
            await session_category.create_voice_channel("Voice Chat")
            session.room = session_category
            # attach user ids and channel ids to OH room info in channel authority
            ca: ChannelAuthority = ChannelAuthority(self.guild)

            await self.safe_delete(session.announcement)

            ca.add_oh_session(session)
            await text_channel.send("Hi, {} and {}!  Let the learning commence!  Type !close to end the session!".format(
                session.member.mention,
                session.ta.mention,
            ))
            await text_channel.send('The question asked/help requested was: {}'.format(session.request))
            logger.info("OH session for {} accepted by {}".format(
                command.name(session.member),
                command.name(self.message.author)))
            await self.safe_delete(self.message, admonition='Deleting the accept message can potentially cause errors, allow me to delete it for you.')

        else:
            await self.message.channel.send('The session member is still null, this should never happen of course.  ')


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
