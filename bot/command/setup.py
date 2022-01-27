import logging

from discord import Message, Client, Member, TextChannel, CategoryChannel, PermissionOverwrite, Role, Permissions
from typing import Optional

import command
import mongo
from channels import ChannelAuthority
from roles import RoleAuthority

logger = logging.getLogger(__name__)


@command.command_class
class SetupCommand(command.Command):
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

        admin_category = "Administration"
        staff_category = "Instruction"
        student_category = "Course Rooms"
        waiting_room_name = "waiting-room"
        queue_room_name = "student-requests"
        auth_channel_name = 'landing-pad'
        maintenance_channel_name = 'maintenance'
        channel_structure = {
            DMZ_category: {
                "text": ["announcements", "landing-pad"],
                "voice": [],
            },
            admin_category: {
                "text": ['maintenance', 'course-admin', 'instructor-lounge'],
                "voice": ['instructor-lounge']
            },
            staff_category: {
                "text": ["ta-announcements", 'ta-general', 'grading', 'random-and-meme', queue_room_name],
                "voice": ['ta-general', 'grading'],
            },
            student_category: {
                "text": ["general", "tech-support", "memes", waiting_room_name],
                "voice": ["questions"],
            }
        }

        categories = {}
        all_channels = {}  # Replicates channel_structure, but with Channel objects
        waiting_room: Optional[TextChannel] = None
        queue_room: Optional[TextChannel] = None
        auth_room: Optional[TextChannel] = None
        maintenance_room: Optional[TextChannel] = None
        for category, channels in channel_structure.items():
            text, voice = (channels["text"], channels["voice"])
            category_channel: CategoryChannel = await self.guild.create_category(category)

            categories[category] = category_channel
            all_channels[category] = {"text": {}, "voice": {}}

            for name in text:
                channel = await category_channel.create_text_channel(name)
                if name == maintenance_channel_name:
                    maintenance_room = channel
                elif name == auth_channel_name:
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
        everyone_role: Optional[Role] = None
        for role in self.guild.roles:
            if role.name == "@everyone":
                everyone_role = role
                break

        remove_read: PermissionOverwrite = PermissionOverwrite(read_messages=False)
        add_read: PermissionOverwrite = PermissionOverwrite(read_messages=True)
        remove_media: PermissionOverwrite = PermissionOverwrite(attach_files=False, embed_links=False)
        add_media: PermissionOverwrite = PermissionOverwrite(attach_files=True, embed_links=True, read_messages=True)
        # Overwrite Administrator's Area category read permissions
        await categories[admin_category].set_permissions(admin_role, overwrite=add_read)
        await categories[admin_category].set_permissions(ta_role, overwrite=remove_read)
        await categories[admin_category].set_permissions(student_role, overwrite=remove_read)
        await categories[admin_category].set_permissions(un_authed_role, overwrite=remove_read)
        await categories[admin_category].set_permissions(everyone_role, overwrite=remove_read)
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
        await all_channels[DMZ_category]["text"]["landing-pad"].set_permissions(ta_role, overwrite=remove_read)
        await all_channels[DMZ_category]["text"]["landing-pad"].set_permissions(student_role, overwrite=remove_read)

        logger.info("Updating channel authority with UUIDs {} and {}".format(waiting_room.id, queue_room.id))
        channel_authority: ChannelAuthority = ChannelAuthority(self.guild)
        channel_authority.save_channels(categories[DMZ_category], waiting_room, queue_room, auth_room, maintenance_room)

        await first.send("Righto! You're good to go, boss!")

    async def generate_roles(self, guild, admin_permissions, ta_permissions, student_permissions,
                             un_authed_permissions):
        # Adding roles -- do NOT change the order without good reason!
        admin_role: Role = await guild.create_role(name="Admin", permissions=admin_permissions, mentionable=True,
                                                   hoist=True)
        # await admin.edit(position=4)
        logger.info("Created role Admin")
        ta_role: Role = await guild.create_role(name="TA", permissions=ta_permissions, mentionable=True,
                                                hoist=True)
        # await ta_role.edit(position=3)
        logger.info("Created role TA")
        student_role: Role = await guild.create_role(name="Student", permissions=student_permissions, mentionable=True,
                                                     hoist=True)
        # await student_role.edit(position=2)  # just above @everyone
        logger.info("Created role Student")
        un_authed_role: Role = await guild.create_role(name="Unauthed", permissions=un_authed_permissions,
                                                       mentionable=True,
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
                                   embed_links=True,
                                   attach_files=True)
        admin_permissions: Permissions = Permissions.all()
        un_authed_permissions: Permissions = Permissions.none()
        un_authed_permissions.update(read_message_history=True,
                                     read_messages=False,
                                     send_messages=False)
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
        if command.is_bot_mentioned(message, client) and ("setup" in message.content or "set up" in message.content):
            ra: RoleAuthority = RoleAuthority(message.guild)
            if ra.is_admin(message.author):
                return True
            else:
                if ca.waiting_channel is None:
                    return True
                await message.channel.send("You can't run setup, " + message.author.mention)
                return False
        return False
