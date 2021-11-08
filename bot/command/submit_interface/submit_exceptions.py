

class AlreadyClosingException(Exception):
    def __init__(self, message, assignment):
        self.message = message
        self.assignment = assignment