from enum import Enum


class Command(Enum):
    START = '/start'
    HELP = '/help'
    VOLUME = '/volume'
    TOPVOLUME = '/topvolume'
    ADMIN = '/admin'
    CODE = '/code'
    SENTIMENT = '/sentiment'
    ASSETS = '/assets'
    

def match_command(message):
    for command in Command:
        if message.startswith(command.value):
            return command
    return None
