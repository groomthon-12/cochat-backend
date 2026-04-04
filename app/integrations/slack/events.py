from enum import Enum


class SlackEventType(str, Enum):
    MESSAGE = "message"
    APP_MENTION = "app_mention"
