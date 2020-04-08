# TA Bot Help
Hello!  Thanks for helping out with office hours on discord.  Discord is a online text and voice chat system originally designed for gamers -- we're using it to run office hours.

## Global commands
These are commands that can be run by all channel members.

### View the queue status
If you type `!status` you will be able to see how many students are waiting in the queue.  We are aware that this command leaves a lot to be desired and improving it is high on our TODO list.

### Viewing this help page
Typing `!help` will provide a link to role-specific help.

## TA/Admin commands
The following are commands the bot will accept from only TAs or Admins.

### Accepting a student from the waiting queue
If you type `!accept` in the student-requests channel, it take the oldest request message from the student-requrests channel, and generate a special channel for you and the student that you accepted.  The bot will mention you in that new room so your attention will be brought to that channel.

In the OH session channel, you can type to the student in the text channel, or speak with them over voice in the voice channel.  Also, at the bottom of the channel list there is a computer icon with an arrow in it.  Pressing that button will let you share your screen with the student.

Once you have finished helping the student, you can may end the session with the `!close` command.  This will remove the channel.

NOTE:  all course staff can see all of the OH session channels.  This means that occasionally someone might pop in to help out.  This is great!

### Rejecting a student from the queue

If a student has no message, or they have been repeatedly entering the queue at the expense of others, or if their message is a simple question you can answer, you can reject them from the queue.  You can reject students from any point in the queue.  The command is `!reject [user id] [reason]`.  You MUST supply a reason, and your message will stay in the chat, so please be polite to students -- they are just here for help.

### Opening and closing office hours

WARNING!  Taking either of these actions will clear the queue!  Only use these commands if NO ONE ELSE IS CURRENTLY HELPING STUDENTS.

To close office hours, mention the bot (e.g. @201bot) and say `oh end`.  To start office hours, mention the bot and say `oh start`.

## Student commands
While you are unlikely to use these commands, they are documented here so that you can help any student that is having difficulty properly using the bot.

### Authentication
When a student first joins the server, they are put into the landing-pad room.  From there, they are instructed to log in using a personal code they were sent via email.  They do this by going to the authentication channel and typing `!auth [their code]`.

This is a one-time thing for them.  Once they are authenticated, they are assigned their real name and allowed into student spaces.

### Requesting Help
Students have a channel, waiting-room, wherein they can use the `!request [description of their request]` command.  This will put them into a waiting queue to get help from course staff.
