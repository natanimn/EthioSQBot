from telebot import TeleBot
from telebot.custom_filters import SimpleCustomFilter
from database import Database as db


class LangCode(SimpleCustomFilter):
    key = 'lang_code'

    @classmethod
    def check(self, message):
        return db.lang_code(message.from_user.id)


class NoState(SimpleCustomFilter):
    key = 'no_state'

    def __init__(self, bot: TeleBot):
        self.bot = bot

    def check(self, message):
        user_id = message.from_user.id
        try:
            state = self.bot.get_state(user_id)

            if state is None:
                return True
            else:
                return False
        except KeyError:

            return True


class Deeplink(SimpleCustomFilter):
    key = 'is_deeplink'

    def check(self, message):
        return len(message.text.split()) > 1 and message.text.startswith('/start')


class IsAdmin(SimpleCustomFilter):
    key = 'is_admin'

    def check(self, message):
        user_id = message.from_user.id
        return db('').user(user_id).status in ['owner', 'admin']