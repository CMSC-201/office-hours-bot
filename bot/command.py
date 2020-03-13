import json

commands = {"close":office_close,
            "auth":student_authenticate,
            "request":request_create,
            "accept":request_accept}

def parse_arguments(msg, prefix):
    args = []
    if msg.content.startswith(prefix):
        params = msg.content[:1].split()
        for param in params:
            args.append(param)
    return args
    
def execute_command(msg, args, uuids):
    cmd = args[0]
    if cmd in commands:
        cmd(msg, args, uuids)

def office_close(msg, args, uuids):
    room = None
    queue = read_json('../offices.json')
    for office in queue["occupied"]:
        if office["room"] == msg.channel.id:
            room = office
            queue["occupied"].remove(room)
    # Begin closing the room if occupied
    if room:
        room_chan = msg.guild.get_channel(room)
        room_role = msg.guild.get_role(room)
        # Take the role from teachers and students
        teacher, student = None, None
        while len(room["teachers"]) > 0:
            teacher = room["teachers"].pop()
            msg.guild.get_member(teacher).remove_roles(room_role)
        while len(room["students"]) > 0:
            student = room["students"].pop()
            msg.guild.get_member(student).remove_roles(room_role)
        # Clear all message objects from room
        room_chan.purge(limit=1000)
        # Mark room as vacant
        queue["openRooms"].append(room)
        
    # Remove command from channel immediately
    msg.delete()
    # Save state
    write_json('../offices.json', queue)

def student_authenticate(msg, args, uuids):
    # No key in command
    if len(args) < 2:
        response = msg.channel.send("Please provide your code in this format:",
                                    "`!auth (key)`")
        response.delete(delay=15)
        msg.delete()
        return

    students = read_json('../studenthash.json')
    name = None
    key = args[1]
    # Find student's hash key
    for student in students["unauthed"]:
        if key == student["id"]:
            name = student["name"]
            students["authed"].append(student)
            students["unauthed"].remove(student)
    # Student exists, begin authentication process
    if name:
        response = msg.channel.send("You have been authenticated! Please go to <#>")
        response.delete(delay=15)
        author = msg.author.id
        role = msg.guild.get_role(uuids["StudentRole"])
        # Assign student and name
        msg.guild.get_member(author).add_roles(role)
        msg.guild.get_member(author).edit(nick=name)
    # Student does not exist, perhaps an incorrect code
    else:
        response = msg.channel.send("You have not given a valid code, or the",
                                    "code has already been used.\n",
                                    "Please contact a professor or Min.")
        response.delete(delay=15)

    # Remove command from channel immediately
    msg.delete()

def request_create(msg, args, uuids):
    pass

def request_accept(msg, args, uuids):
    pass

def read_json(path):
    with open(path, "r") as f:
        return json.load(f)

def write_json(path, data):
    with open(path, "w+") as f:
        f.write(json.dumps(data))