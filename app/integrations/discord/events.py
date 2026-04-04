from enum import Enum


class DiscordEventType(str, Enum):
    MESSAGE_CREATE = "MESSAGE_CREATE"
    MESSAGE_EDIT = "MESSAGE_EDIT"
    MESSAGE_DELETE = "MESSAGE_DELETE"
