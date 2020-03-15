import json
import logging
import os

import discord
from discord import Message, Guild, CategoryChannel, Role, Permissions, PermissionOverwrite, TextChannel, Member

import command as com
from channels import ChannelAuthority
from command import handle_message
from globals import get_globals

logger = logging.getLogger('bot_main')


class MyClient(discord.Client):
    def __init__(self, **options):
        super().__init__(**options)
        self.channel_authority: ChannelAuthority = None

    async def on_ready(self):
        logger.info('Logged on as {0}!'.format(self.user))
        if len(self.guilds) > 1:
            raise ValueError("Bot cannot manage more than one guild at this time.")

        logger.info("Loading channel authority")
        self.channel_authority = ChannelAuthority(self.guilds[0])

    async def on_message(self, message: Message):
        # if message.content.startswith('hashbot'):
        #    await message.channel.send('https://gph.is/28LBdcE')
        guild: Guild = message.guild
        logger.info('Message from {0.author}: {0.content}'.format(message))
        if com.is_bot_mentioned(message, self):
            if "set up" in message.content or "setup" in message.content:
                await self.setup(guild, message)


        # Ignore bot messages
        if message.author.bot:
            return
        # Split message by spaces
        args = com.parse_arguments(message, prefix)
        # If not a command, ignore
        if not args:
            return

        logger.info('{0.author} issued command: {0.content}'.format(message))
        response = await com.execute_command(message, args, uuids)
        if response:
            logger.info(response)

        await handle_message(message, self)

    async def setup(self, guild: Guild, message: Message):
        DMZ_category = "Bulletin Board"
        author: Member = message.author
        if not author.guild_permissions.administrator:
            await message.channel.send("Nice try, " + author.mention + ". I'm not fooled so easily.")
            return

        if DMZ_category in [c.name for c in guild.categories]:
            await message.channel.send(
                "Foolish mortal, we are already prepared! " +
                "Delete the Bulletin Board category if you want to remake the world!")
            return

        # delete all the existing channels
        for channel in guild.channels:
            await channel.delete()

        first = None

        admin_permissions, student_permissions, un_authed_perms = await self.generate_permissions()

        # Delete ALL old roles
        for role in guild.roles:
            try:
                await role.delete()
                logger.info("Deleted role {}".format(role.name))
            except:
                logger.warning("Unable to delete role {}".format(role.name))

        student_role, un_authed = await self.generate_roles(admin_permissions, guild, student_permissions,
                                                            un_authed_perms)

        staff_category = "Instructor's Area"
        student_category = "Student's Area"
        waiting_room_name = "waiting-room"
        queue_room_name = "student-requests"
        channel_structure = {
            DMZ_category: {
                "text": ["landing-pad", "getting-started", "announcements", "authentication"],
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
        waiting_room: TextChannel = None
        queue_room: TextChannel = None
        for category, channels in channel_structure.items():
            text, voice = (channels["text"], channels["voice"])
            category_channel: CategoryChannel = await guild.create_category(category)

            categories[category] = category_channel

            for name in text:
                channel = await category_channel.create_text_channel(name)
                if name == queue_room_name:
                    queue_room = channel
                elif name == waiting_room_name:
                    waiting_room = channel
                if not first:
                    first = channel
                logger.info("Created text channel {} in category {}".format(name, category))

            for name in voice:
                await category_channel.create_voice_channel(name)
                logger.info("Created voice channel {} in category {}".format(name, category))

        logger.info("Setting up channel overrides for {} and {}".format(categories[staff_category].name,
                                                                        categories[student_category].name))
        overwrite: PermissionOverwrite = PermissionOverwrite(read_messages=False)
        await categories[staff_category].set_permissions(student_role, overwrite=overwrite)
        await categories[staff_category].set_permissions(un_authed, overwrite=overwrite)
        await categories[student_category].set_permissions(un_authed, overwrite=overwrite)

        logger.info("Updating channel authority with UUIDs {} and {}".format(waiting_room.id, queue_room.id))
        self.channel_authority.save_channels(waiting_room, queue_room)

        await first.send("Righto! You're good to go, boss!")

    async def generate_roles(self, admin_permissions, guild, student_permissions, un_authed_perms):
        # Adding roles -- do NOT change the order without good reason!
        admin: Role = await guild.create_role(name="Admin", permissions=admin_permissions, mentionable=True, hoist=True)
        # await admin.edit(position=4)
        logger.info("Created role admin")
        ta_role: Role = await guild.create_role(name="TA", permissions=student_permissions, mentionable=True,
                                                hoist=True)
        # await ta_role.edit(position=3)
        logger.info("Created role TA")
        student_role: Role = await guild.create_role(name="Student", permissions=student_permissions, mentionable=True,
                                                     hoist=True)
        # await student_role.edit(position=2)  # just above @everyone
        logger.info("Created role Student")
        un_authed: Role = await guild.create_role(name="Unauthed", permissions=un_authed_perms, mentionable=True,
                                                  hoist=True)
        # await un_authed.edit(position=1)
        logger.info("Created role Unauthed")
        return student_role, un_authed

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
                                   use_voice_activation=True)
        admin_permissions: Permissions = Permissions.all()
        un_authed_perms: Permissions = Permissions.none()
        un_authed_perms.update(read_message_history=True,
                               read_messages=True,
                               send_messages=True)
        ta_permissions: Permissions = Permissions.all()
        ta_permissions.update(administrator=False,
                              admin_permissions=False,
                              manage_channels=False,
                              manage_guild=False,
                              manage_roles=False,
                              manage_permissions=False,
                              manage_webhooks=False, )
        return admin_permissions, student_permissions, un_authed_perms


def set_up_logs():
    FORMAT = '%(asctime)s:%(levelname)s:%(name)s: %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.INFO)

    handler = logging.FileHandler(filename='discord.log', encoding='utf-8',
                                  mode='a')
    handler.setFormatter(logging.Formatter(FORMAT))
    handler.setLevel(logging.INFO)

    logging.getLogger().addHandler(handler)

    logger.info("========NEW SESSION=========")


if __name__ == '__main__':
    set_up_logs()
    client = MyClient()
    info = get_globals()
    if info:
        token = info['props']['token']
        prefix = info['props']['prefix']
        uuids = info['uuids']
        client.run(token)
    else:
        print("Something failed (this is very vague)")
