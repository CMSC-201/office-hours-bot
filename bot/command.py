

def parse_arguments(msg, prefix):
    args = []
    if msg.content.startswith(prefix):
        params = msg.content[:1].split()
        for param in params:
            args.append(param)
    return args
    
