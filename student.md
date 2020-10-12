# Student Bot Help
Hello!  Discord is a online text and voice chat system originally designed for gamers -- we're using it to run office hours.

## Global commands
These are commands that can be run by all channel members.

### View the queue status
If you type `!status` you will be able to see how many students are waiting in the queue.  We are aware that this command leaves a lot to be desired and improving it is high on our TODO list.

### Viewing this help page
Typing `!help` will provide a link to role-specific help.

## Student commands
The following are commands useable to you to access the server and request help for office hours.

### Authentication
When you first join the server, you are put into the landing-pad room.  You should then switch to the authentication channel and authenticate.  You do this by typing `!auth [you code]`.

This is a one-time thing.  Once you are authenticated, you are assigned your real name and allowed into student spaces.

### Requesting Help
Once you are authenticated, you can go to the channel waiting-room, wherein you can use the `!request [description of you request]` command.  This will put you into a waiting queue to get help from course staff.

### Checking Queue Status
Once you have requested help and are in the waiting queue, you will be able to check your queue status using the command:

`!status`

Upon running the command, the bot will DM you with your position in the queue. If you are not in the queue, it will notify you that you are not in the queue.

### Locating Lecture
Invoking the command

`!where is the lecture today`

or

`!where are the lectures today`

will have the bot send you a DM with a link to that day's lecture. If there is no lecture that day, the bot will notify you that there is no lecture.

### Checking In
When you attend your lab section, you are required to check in *twice* to receive the full 2 attendance points. The TA will allow first check-in at the beginning of the lab section, and a second check-in will occur later on in the lab section.
You can check in by sending the

`!check in`

command in your lab section channel. The bot should DM you a confirmation that your attendance has been counted.
Upon second check-in, the bot will notify you that you have completed your attendance requirements.

