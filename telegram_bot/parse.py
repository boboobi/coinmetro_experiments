"""Helper functions for parsing telegram messages."""


def get_argument_list(message):
    return message.strip().split(" ")
    

def get_argument_at_index(message, index=0):
    if message is not None:
        arguments = get_argument_list(message)
        if len(arguments) > index:
            return arguments[index]
    return None


def get_numerical_argument_at_index(message, index=0):
    argument = get_argument_at_index(message, index)
    try:
        return int(argument)
    except:
        return None
