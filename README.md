# Office Hours Chat Bot

Requires that you run `heroku config:set BOT_TOKEN=[]` token for it to run on heroku.

If you are developing locally, you can create a copy of `sample-prop.json` and put in your values.

Remember not to version private keys!

## Setup

You must have developer mode enabled on your Discord client in order to proceed.
1. Go to User Settings on your Discord Client
2. In the settings, go to Appearance
3. One of the options should be named Developer Mode, toggle it on.
4. You may now right click servers (guilds), channels, messages, and users and click Copy ID to get their Discord UID.

### JSON File Guide

#### sample-prop.json
You will be copying this and changing this to `prop.json`. Sensitive info will be going here.
There are 3 values to change.
- `token`: Bot Token - You may retrieve this token from your bot page from the Discord Developers site. Do not share this information with anyone.
- `prefix`: String - Generally, bots may use a prefix such as `!` to listen for commands. For example, `!request`. This may be changed to your liking.
- `mongodb-address`: 

#### uuids.json
In `uuids.json`, you will have 5 values to change. These are where you will be putting Discord UIDs.
- `Server`: Guild ID (Right click the server icon on the left hand side for the ID)
- `WaitingRoom`: Channel ID - This is the channel where students will request for help.
- `RequestsRoom`: Channel ID - This is the channel where TAs and professors may accept the requests.
- `AuthRoom`: Channel ID - This is where students will verify their identity as a student of the class.
- `StudentRole`: Role ID - This is the role assigned to student after authentication. To get this ID, right click on the desired student role in your Discord server's settings, in the Roles section.

#### student_queue.json
In `student_queue.json`, you'll only have an empty array at first.
Over time, when students send in requests, they will be processed and placed into a JSON object, which is then placed into the array and treated like a queue.
This is an example format of two students in the queue:
```javascript
[
    {"userID": (user discord id), "requestID": (request message id)},
    {"userID": (another user id), "requestID": (their request id)}
]
```
You don't need to modify these values at all, since they will be fully managed by the bot.

#### offices.json
In `offices.json`, there are multiple properties that you will have to implement yourself.
By default, you may leave `is_open` and `open_indicator` as false and 0, respectively. They will be automatically overwritten when the bot is officially running.
The `room_template` is a template for the JSON object that you will be entering into the `all_rooms` array.
This template does not get touched or used by the bot at all, and its purpose is entirely for the setup process.
- `room`: Channel ID - The channel where an office can be held.
- `key`: Role ID - The role that is given to TAs, professors, and students when a request gets accepted. This role must have exclusive access to the office channel that it applies to.
- `teachers`: Array of User IDs - You may copy this along with the template without modifying. Its contents are fully managed by the bot. (It will contain IDs of the TAs that are helping)
- `students`: Array of User IDs - You may copy this along with the template without modifying. Its contents are fully managed by the bot. (It will contain IDs of the students being helped)
Once you have placed the appropriate amount of offices into your `all_rooms` array, you may copy everything into the `open_rooms` array as well.
`all_rooms` will serve as a "reset list" in case any office data gets lost in a dramatic accident.
`occupied` is an array, fully managed by the bot, that will contain the office data from `open_rooms` when someone accepts a student's request.