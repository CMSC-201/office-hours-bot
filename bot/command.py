import logging
from datetime import datetime as dt

import discord
from discord import Message, Guild, Client, Member, TextChannel, CategoryChannel, PermissionOverwrite, Role, Permissions

from channels import ChannelAuthority
from member import MemberAuthority
from queues import QueueAuthority, OHSession
from roles import RoleAuthority

logger = logging.getLogger(__name__)


def name(member: Member):
    return member.nick if member.nick else member.display_name


def is_bot_mentioned(message: Message, client: Client) -> bool:
    users_mentioned_in_role = []
    for role in message.role_mentions:
        users_mentioned_in_role.extend(role.members)

    if client.user in message.mentions or client.user in users_mentioned_in_role:
        return True

    return False


supported_commands = []


def command_class(cls):
    supported_commands.append(cls)


async def handle_message(message: Message, client: Client):
    if not message.guild:
        return  # this is a DM to the bot TODO: add DM commands
    for cmd_class in supported_commands:
        if await cmd_class.is_invoked_by_message(message, client):
            command = cmd_class(message, client)
            await command.handle()
            return


class Command:
    def __init__(self, message: Message = None, client: Client = None):
        if not message:
            raise ValueError("You must issue a command with a message or guild")
        self.message: Message = message
        self.guild: Guild = message.guild
        self.client = client

    async def handle(self):
        raise AttributeError("Must be overwritten by command class")

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        pass


@command_class
class Bark(Command):
    async def handle(self):
        await self.message.channel.send("Ruff!")

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return message.content.startswith("!bark")


@command_class
class SetupCommand(Command):
    async def handle(self):
        DMZ_category = "Bulletin Board"
        author: Member = self.message.author
        if not author.guild_permissions.administrator:
            await self.message.channel.send("Nice try, " + author.mention + ". I'm not fooled so easily.")
            return

        if DMZ_category in [c.name for c in self.guild.categories]:
            await self.message.channel.send(
                "Foolish mortal, we are already prepared! " +
                "Delete the Bulletin Board category if you want to remake the world!")
            return

        # delete all the existing channels
        for channel in self.guild.channels:
            await channel.delete()

        first = None

        admin_permissions, ta_permissions, student_permissions, un_authed_permissions = await self.generate_permissions()

        # Delete ALL old roles
        for role in self.guild.roles:
            try:
                await role.delete()
                logger.info("Deleted role {}".format(role.name))
            except:
                logger.warning("Unable to delete role {}".format(role.name))

        admin_role, ta_role, student_role, un_authed_role = await self.generate_roles(self.guild, admin_permissions,
                                                                                 ta_permissions,
                                                                                 student_permissions,
                                                                                 un_authed_permissions)

        staff_category = "Instructor's Area"
        student_category = "Student's Area"
        waiting_room_name = "waiting-room"
        queue_room_name = "student-requests"
        auth_room_name = "authentication"
        channel_structure = {
            DMZ_category: {
                "text": ["landing-pad", "getting-started", "announcements", auth_room_name],
                "voice": [],
            },
            staff_category: {
                "text": ["course-staff-general", queue_room_name],
                "voice": ["instructor-lounge", "ta-lounge"],
            },
            student_category: {
                "text": ["general", "tech-support", "memes", waiting_room_name],
                "voice": ["questions"],
            }
        }

        categories = {}
        all_channels = {} # Replicates channel_structure, but with Channel objects
        waiting_room: TextChannel = None
        queue_room: TextChannel = None
        auth_room: TextChannel = None
        for category, channels in channel_structure.items():
            text, voice = (channels["text"], channels["voice"])
            category_channel: CategoryChannel = await self.guild.create_category(category)

            categories[category] = category_channel
            all_channels[category] = {"text":{},"voice":{}}

            for name in text:
                channel = await category_channel.create_text_channel(name)
                if name == auth_room_name:
                    auth_room = channel
                elif name == queue_room_name:
                    queue_room = channel
                elif name == waiting_room_name:
                    waiting_room = channel
                if not first:
                    first = channel
                all_channels[category]["text"][name] = channel
                logger.info("Created text channel {} in category {}".format(name, category))

            for name in voice:
                await category_channel.create_voice_channel(name)
                all_channels[category]["voice"][name] = channel
                logger.info("Created voice channel {} in category {}".format(name, category))

        logger.info("Setting up channel overrides for {} and {}".format(categories[staff_category].name,
                                                                        categories[student_category].name))
        everyone_role: Role = None
        for role in self.guild.roles:
            if role.name == "@everyone":
                everyone_role = role
        remove_read: PermissionOverwrite = PermissionOverwrite(read_messages=False)
        add_read: PermissionOverwrite = PermissionOverwrite(read_messages=True)
        remove_media: PermissionOverwrite = PermissionOverwrite(attach_files=False, embed_link=False)
        add_media: PermissionOverwrite = PermissionOverwrite(attach_files=True, embed_link=True)
        # Overwrite Instructor's Area category read permissions
        await categories[staff_category].set_permissions(admin_role, overwrite=add_read)
        await categories[staff_category].set_permissions(ta_role, overwrite=add_read)
        await categories[staff_category].set_permissions(student_role, overwrite=remove_read)
        await categories[staff_category].set_permissions(un_authed_role, overwrite=remove_read)
        await categories[staff_category].set_permissions(everyone_role, overwrite=remove_read)
        # Overwrite Student's Area category read permissions
        await categories[student_category].set_permissions(admin_role, overwrite=add_read)
        await categories[student_category].set_permissions(ta_role, overwrite=add_read)
        await categories[student_category].set_permissions(student_role, overwrite=add_read)
        await categories[student_category].set_permissions(un_authed_role, overwrite=remove_read)
        await categories[student_category].set_permissions(everyone_role, overwrite=remove_read)
        # Overwrite Student's Area category media posting permissions
        await categories[student_category].set_permissions(student_role, overwrite=remove_media)
        await all_channels[student_category]["text"]["memes"].set_permissions(student_role, overwrite=add_media)
        # Overwrite Bulletin Board category read permissions
        await categories[DMZ_category].set_permissions(everyone_role, overwrite=add_read)
        await all_channels[DMZ_category]["text"][auth_room_name].set_permissions(ta_role, overwrite=remove_read)
        await all_channels[DMZ_category]["text"][auth_room_name].set_permissions(student_role, overwrite=remove_read)
        await all_channels[DMZ_category]["text"]["landing-pad"].set_permissions(ta_role, overwrite=remove_read)
        await all_channels[DMZ_category]["text"]["landing-pad"].set_permissions(student_role, overwrite=remove_read)

        logger.info("Updating channel authority with UUIDs {} and {}".format(waiting_room.id, queue_room.id))
        channel_authority: ChannelAuthority = ChannelAuthority(self.guild)
        channel_authority.save_channels(waiting_room, queue_room, auth_room)

        await first.send("Righto! You're good to go, boss!")

    async def generate_roles(self, guild, admin_permissions, ta_permissions, student_permissions, un_authed_permissions):
        # Adding roles -- do NOT change the order without good reason!
        admin_role: Role = await guild.create_role(name="Admin", permissions=admin_permissions, mentionable=True, hoist=True)
        # await admin.edit(position=4)
        logger.info("Created role Admin")
        ta_role: Role = await guild.create_role(name="TA", permissions=student_permissions, mentionable=True,
                                                hoist=True)
        # await ta_role.edit(position=3)
        logger.info("Created role TA")
        student_role: Role = await guild.create_role(name="Student", permissions=ta_permissions, mentionable=True,
                                                     hoist=True)
        # await student_role.edit(position=2)  # just above @everyone
        logger.info("Created role Student")
        un_authed_role: Role = await guild.create_role(name="Unauthed", permissions=un_authed_permissions, mentionable=True,
                                                  hoist=True)
        # await un_authed.edit(position=1)
        logger.info("Created role Unauthed")
        return admin_role, ta_role, student_role, un_authed_role

    async def generate_permissions(self):
        # role permissions
        student_permissions: Permissions = Permissions.none()
        student_permissions.update(add_reactions=True,
                                   stream=True,
                                   read_message_history=True,
                                   read_messages=True,
                                   send_messages=True,
                                   connect=True,
                                   speak=True,
                                   use_voice_activation=True,
                                   embed_link=True,
                                   attach_files=True)
        admin_permissions: Permissions = Permissions.all()
        un_authed_permissions: Permissions = Permissions.none()
        un_authed_permissions.update(read_message_history=True,
                               read_messages=True,
                               send_messages=True)
        ta_permissions: Permissions = Permissions.all()
        ta_permissions.update(administrator=False,
                              admin_permissions=False,
                              manage_channels=False,
                              manage_guild=False,
                              manage_roles=False,
                              manage_permissions=False,
                              manage_webhooks=False)
        return admin_permissions, ta_permissions, student_permissions, un_authed_permissions

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        ca: ChannelAuthority = ChannelAuthority(message.guild)
        if is_bot_mentioned(message, client) and ("setup" in message.content or "set up" in message.content):
            ra: RoleAuthority = RoleAuthority(message.guild)
            if ra.admin in message.author.roles:
                return True
            else:
                if ca.waiting_channel == None:
                    return True
                await message.channel.send("You can't run setup, " + message.author.mention)
                return False
        return False


async def is_lab_command(message: Message, client: Client, keyword: str):
    ca: ChannelAuthority = ChannelAuthority(message.guild)
    if is_bot_mentioned(message, client) and \
            ("{} lab".format(keyword) in message.content or "lab {}".format(keyword) in message.content):
        if ca.lab_running() and keyword == "start":
            await message.channel.send("A lab is already running, " + message.author.mention + \
                                       ", please wait for it to conclude or join in.")
            return False
        if message.channel == ca.queue_channel:
            ra: RoleAuthority = RoleAuthority(message.guild)
            if ra.ta_or_higher(message.author):
                return True
            else:
                await message.channel.send("You can't do this, " + message.author.mention)
                return False
        else:
            await message.channel.send("You have to be in " + ca.queue_channel.mention + " to request a lab start.")
            return False
    return False


@command_class
class StartLab(Command):
    async def handle(self):
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        await ca.start_lab(self.message)
        logger.info("Lab started by {}".format(
            name(self.message.author)
        ))

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return await is_lab_command(message, client, "start")


@command_class
class EndLab(Command):
    async def handle(self):
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        await ca.end_lab(self.message)

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return await is_lab_command(message, client, "end")


@command_class
class EnterQueue(Command):
    async def handle(self):
        qa: QueueAuthority = QueueAuthority(self.guild)
        request = "[Student did not supply text]"
        if " " in self.message.content:
            # remove the !request from the front of the message
            request = " ".join(self.message.content.split()[1:])

        ca: ChannelAuthority = ChannelAuthority(self.guild)

        # Build embedded message
        color = discord.Colour(0).blue()
        embeddedMsg = discord.Embed(description=request,
                                    timestamp=dt.now(),
                                    colour=color)

        author: Member = self.message.author
        embeddedMsg.set_author(name=name(author))
        embeddedMsg.add_field(name="Accept request by typing",
                              value="!accept")
        # Send embedded message
        announcement = await ca.queue_channel.send(embed=embeddedMsg)
        qa.add_to_queue(author, request, announcement)
        await self.message.delete()
        logger.info("{} added to queue with request text: {}".format(
            name(author),
            request
        ))

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        ca: ChannelAuthority = ChannelAuthority(message.guild)
        if message.content.startswith("!request"):
            qa: QueueAuthority = QueueAuthority(message.guild)
            if not qa.is_office_hours_open():
                warning = await message.channel.send(
                    "Office hours are closed.  Please try again after they have opened.".format(
                        message.author.mention,
                        ca.waiting_channel.mention))
                await warning.delete(delay=7)
                await message.delete()
                return False
            if qa.is_member_in_queue(message.author):
                warning = await message.channel.send(
                    "{} you are already in the queue.  Please continue waiting.".format(
                        message.author.mention,
                        ca.waiting_channel.mention))
                await warning.delete(delay=7)
                await message.delete()
                return False
            if message.channel == ca.waiting_channel:
                return True
            else:
                warning = await message.channel.send("{} you must be in {} to request a place in the queue.".format(
                    message.author.mention,
                    ca.waiting_channel.mention))
                await warning.delete(delay=7)
                await message.delete()
                return False
        return False


@command_class
class QueueStatus(Command):
    async def handle(self):
        qa: QueueAuthority = QueueAuthority(self.guild)
        queue = qa.retrieve_queue()
        await self.message.channel.send(
            "{}, there are {} in the queue presently.  We appreciate your patience.".format(
                self.message.author.mention,
                len(queue)
            ))

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!status"):
            return True

        return False


@command_class
class AcceptStudent(Command):
    async def handle(self):
        qa: QueueAuthority = QueueAuthority(self.guild)
        # get oldest queue item (and also remove it)
        session: OHSession = await qa.dequeue(self.message.author)

        # create role for channel
        role: Role = await self.guild.create_role(name="{}'s OH session".format(name(session.member)), hoist=True)
        num_roles = len(self.guild.roles)
        # todo find bot role insert this underneath
        # await role.edit(position=num_roles-2)
        session.role = role
        await session.member.add_roles(session.role)
        await self.message.author.add_roles(session.role)

        # create channel
        ra: RoleAuthority = RoleAuthority(self.guild)
        session_category: CategoryChannel = await self.guild.create_category_channel(
            "Session for {}".format(name(session.member)),
            overwrites={
                role: PermissionOverwrite(read_messages=True, attach_files=True, embed_link=True),
                ra.student: PermissionOverwrite(read_messages=False),
                ra.un_authenticated: PermissionOverwrite(read_messages=False)
            })
        text_channel: TextChannel = await session_category.create_text_channel("Text Cat")
        await session_category.create_voice_channel("Voice chat")
        session.room = session_category
        # attach user ids and channel ids to OH room info in channel authority
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        await session.announcement.delete()
        await self.message.delete()
        ca.add_oh_session(session)
        await text_channel.send("Hi, {} and {}!  Let the learning commence!  Type !close send the session!".format(
            session.member.mention,
            session.ta.mention,
        ))
        logger.info("OH session for {} accepted by {}".format(
            name(session.member),
            name(self.message.author)))

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


@command_class
class EndOHSession(Command):
    async def handle(self):
        await self.message.channel.send("Closing")
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        category_channel: CategoryChannel = None

        # find the correct session
        this_session = None
        for session in ca.get_oh_sessions():
            if self.message.channel in session.room.channels:
                this_session = session
                category_channel = session.room

        # delete the role
        await this_session.role.delete()

        # delete the channels
        for room in category_channel.channels:
            await room.delete()
        await category_channel.delete()

        # remove the session from mongo
        ca.remove_oh_session(category_channel.id)
        logger.info("OH session in room {} closed by {}".format(
            category_channel.id,
            name(self.message.author)))

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!close"):
            ca: ChannelAuthority = ChannelAuthority(message.guild)
            for session in ca.get_oh_sessions():
                if message.channel in session.room.channels:
                    return True
        return False


async def is_oh_command(client, message, type):
    ca: ChannelAuthority = ChannelAuthority(message.guild)
    if is_bot_mentioned(message, client) and \
            ("oh" in message.content.lower() and type in message.content.lower()):
        if message.channel == ca.queue_channel:
            ra: RoleAuthority = RoleAuthority(message.guild)
            if ra.ta_or_higher(message.author):
                return True
            else:
                await message.channel.send("You can't do this, " + message.author.mention)
                return False
        else:
            await message.channel.send("You have to be in " +
                                       ca.queue_channel.mention + " to {} office hours.".format(type))
            return False
    return False

@command_class
class StartOfficeHours(Command):
    async def handle(self):
        qa: QueueAuthority = QueueAuthority(self.guild)
        qa.open_office_hours()
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        await ca.waiting_channel.send(
            "Office hours are live.  Get in line with !request")
        logger.info("Office hours opened by {}".format(
            name(self.message.author)
        ))

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return await is_oh_command(client, message, "start")


@command_class
class EndOfficeHours(Command):
    async def handle(self):
        qa: QueueAuthority = QueueAuthority(self.guild)
        qa.remove_all()
        ca: ChannelAuthority = ChannelAuthority(self.guild)
        await ca.waiting_channel.send(
            "Ok, y'all.  Office hours have ended for now.  An announcement will appear here when they have reopened.")
        logger.info("Office hours closed by {}".format(
            name(self.message.author)
        ))

    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        return await is_oh_command(client, message, "end")




@command_class
class AuthenticateStudent(Command):
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
