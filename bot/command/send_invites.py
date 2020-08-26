import logging

from discord import Message, Client, Attachment
import ssl
import smtplib
import asyncio
import hashlib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import command
import mongo
from globals import get_globals
from queues import QueueAuthority
from roles import RoleAuthority
from channels import ChannelAuthority

logger = logging.getLogger(__name__)


@command.command_class
class SendInvites(command.Command):
    __ADMIN_GROUP = 'admin'
    __TA_GROUP = 'ta'
    __STUDENTS_GROUP = 'student'

    __EMAIL_SETTINGS = 'reflector-email'
    __EMAIL_USERNAME = 'email-username'
    __EMAIL_PASSWORD = 'email-password'
    __TYPE = 'type'

    state_variables = {__EMAIL_USERNAME: '', __EMAIL_PASSWORD: ''}

    def __init__(self, message: Message = None, client: Client = None):
        super().__init__(message, client)
        # there should be one document in the email settings collection, which is the username and password for the reflector email
        self.email_settings_collection = mongo.db[self.__EMAIL_SETTINGS]
        email_settings = self.email_settings_collection.find_one({self.__TYPE: self.__EMAIL_SETTINGS})
        if email_settings:
            self.state_variables[self.__EMAIL_USERNAME] = email_settings[self.__EMAIL_USERNAME]
            self.state_variables[self.__EMAIL_PASSWORD] = email_settings[self.__EMAIL_PASSWORD]


    async def handle(self):

        ra: RoleAuthority = RoleAuthority(self.message.guild)
        ca: ChannelAuthority = ChannelAuthority(self.message.guild)

        if ra.is_admin(self.message.author) and ca.is_maintenance_channel(self.message.channel):
            if self.message.content.startswith('!send invites update'):

                if len(self.message.content.split()) == 5:
                    self.state_variables[self.__EMAIL_USERNAME] = self.message.content.split()[3]
                    self.state_variables[self.__EMAIL_PASSWORD] = self.message.content.split()[4]

                    response = self.email_settings_collection.update_one({self.__TYPE: self.__EMAIL_SETTINGS},
                                                              {'$set': {self.__EMAIL_USERNAME: self.state_variables[self.__EMAIL_USERNAME],
                                                                        self.__EMAIL_PASSWORD: self.state_variables[self.__EMAIL_PASSWORD]}}, upsert=True)
                    # check how many matches were updated...
                    await self.message.channel.send('Updated settings for reflector email.')
                else:
                    await self.message.channel.send('Unable to update settings for reflector email, use !send invites update <username@gmail.com> <password>')
                await self.message.delete()

                return

            elif not self.state_variables[self.__EMAIL_USERNAME] and not self.state_variables[self.__EMAIL_PASSWORD]:
                await self.message.delete()
                await self.message.channel.send('Unable to send, email and password are not set.  ')
                return

            group = self.message.content.split()[3].lower()
            attachment: Attachment = self.message.attachments[0]
            await attachment.save('office_hour_email.html')
            with open('office_hour_email.html') as email_file:
                email_prompt = email_file.read()

            students_group = mongo.db[self.__STUDENTS_GROUP]
            ta_group = mongo.db[self.__TA_GROUP]
            admin_group = mongo.db[self.__ADMIN_GROUP]

            port = 465
            context = ssl.create_default_context()

            server = smtplib.SMTP_SSL("smtp.gmail.com", port, context=context)
            try:
                server.login(self.state_variables[self.__EMAIL_USERNAME], self.state_variables[self.__EMAIL_PASSWORD])
            except smtplib.SMTPAuthenticationError as smtp_auth_error:
                await self.message.channel.send(str(smtp_auth_error))
                return

            users_to_send = []
            if group == 'students' or group == 'all':
                users_to_send.extend(list(students_group.find({})))
            if group == 'tas' or group == 'all':
                users_to_send.extend(list(ta_group.find({})))
            if group == 'admin' or group == 'all':
                users_to_send.extend(list(admin_group.find({})))

            for user in users_to_send:
                student_name = ' '.join([user['First-Name'], user['Last-Name']])
                response = MIMEMultipart('alternative')
                response['From'] = self.state_variables[self.__EMAIL_USERNAME]
                response['To'] = '%s@umbc.edu' % user['UMBC-Name-Id']
                response['Subject'] = '%s, Invitation to Discord Office Hours' % student_name
                formatted_email_prompt = self.format_email(email_prompt, user)
                response.attach(MIMEText(formatted_email_prompt, 'html'))

                try:
                    await self.message.channel.send('Sending email to %s' % user['UMBC-Name-Id'])
                    server.sendmail(self.state_variables['email-username'], response['To'], response.as_string())
                    await asyncio.sleep(4)
                except smtplib.SMTPRecipientsRefused as smtp_recipients_refused:
                    print(smtp_recipients_refused)
                except smtplib.SMTPHeloError as smtp_helo_error:
                    print(smtp_helo_error)
                except smtplib.SMTPSenderRefused as smtp_sender_refused:
                    print(smtp_sender_refused)
                except smtplib.SMTPDataError as smtp_data_error:
                    print(smtp_data_error)
                except smtplib.SMTPNotSupportedError as smtp_not_supported:
                    print(smtp_not_supported)

                await self.message.channel.send('Email invite sent to %s' % student_name)

        else:
            await self.message.channel.send('You are not an administrator, so cannot run this command.')

        await self.message.delete()


    @staticmethod
    async def is_invoked_by_message(message: Message, client: Client):
        if message.content.startswith("!send invites update"):
            if len(message.content.split()) == 5:
                return True
            return False
        elif message.content.startswith("!send invites to"):
            split_message = message.content.split()
            if len(split_message) >= 4 and split_message[3].lower() in ['students', 'tas', 'admin', 'all']:
                if message.attachments:
                    return True
                else:
                    await message.channel.send('You must attach a text or html message to be sent. ')
                    return False
            else:
                return False

        return False

    @staticmethod
    def format_email(email_prompt, student_data):
        for key in student_data:
            replace_key = '{{%s}}' % key
            if replace_key in email_prompt:
                email_prompt = email_prompt.replace(replace_key, student_data[key])
        return email_prompt
