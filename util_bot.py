from typing import Optional
from abc import ABC, abstractmethod
from convertor import time_parse
import json


class DeJson(ABC):
    @classmethod
    @abstractmethod
    def de_json(cls, json_string):
        pass


class User(DeJson):
    @classmethod
    def de_json(cls, json_string):
        return cls(**json_string)

    def __init__(self, name, user_id, date, invites, balance, status, lang_code, gender, link, username, bio,
                 questions, answers, setting, deeplink, withdraw, phone_number):

        self.name: str = name
        self.user_id: int = user_id
        self.date: str = time_parse(date)
        self.invites: Optional[int] = invites
        self.status: str = status
        self.lang_code: Optional[str] = lang_code
        self.gender: Optional[str] = gender or ''
        self.link: [str] = link
        self.username: Optional[str] = username
        self.bio: Optional[str] = bio
        self.balance: Optional[int] = balance
        self.count_question: Optional[int] = questions
        self.count_answers: Optional[int] = answers
        self.setting: Optional[UserSetting] = UserSetting.de_json(setting)
        self.deeplink: Optional[str] = deeplink
        self.withdraw: Optional[int] = withdraw
        self.phone_number: Optional[str] = phone_number

    @property
    def mention(self):
        return f"<a href=\'{self.deeplink+self.link}\'>{self.name}</a> {self.gender}"


class Question(DeJson):
    @classmethod
    def de_json(cls, json_string):
        if isinstance(json_string, str):
            json_string = json.loads(json_string)
        return cls(**json_string)

    def __init__(self, *, asker, date, question_id, message_id, status, browse, question, unique_link, subject, reply,
                 browse_link):
        import json
        self.asker: User = asker
        self.date: str = time_parse(date)
        self.question_id: int = question_id
        self.status: str = status
        self.message_id: int = message_id
        self.browse: str = browse
        self.question: dict = question if not isinstance(question, str) else json.loads(question)
        self.unique_link: str = unique_link
        self.subject: str = subject
        self.reply: bool = reply
        self.browse_link: int = browse_link


class Answer(DeJson):
    @classmethod
    def de_json(cls, json_string):
        if isinstance(json_string, str):
            json_string = json.loads(json_string)
        return cls(**json_string)

    def __init__(self, user_id, question_id, answer_id, date, status, reply_to, unique_link, answer, message_id):
        import json
        self.user_id: User = user_id
        self.question_id: int = question_id
        self.answer_id: int = answer_id
        self.date: str = time_parse(date)
        self.status: str = status
        self.reply_to: int = reply_to
        self.unique_link: str = unique_link
        self.answer: dict = answer if not isinstance(answer, str) else json.loads(answer )
        self.message_id: Optional[int] = message_id


class Setting(DeJson):
    @classmethod
    def de_json(cls, json_string):
        if isinstance(json_string, str):
            json_string = json.loads(json_string)
        return cls(**json_string)

    def __init__(self, admins, restriction):
        self.admins: Optional[dict] = admins
        #self.channels: Optional[dict] = channels
        self.restriction: Optional[Restriction] = Restriction.de_json(restriction)
        #self.ban: Optional[str] = ban


class Restriction(DeJson):
    @classmethod
    def de_json(cls, json_string):
        if isinstance(json_string, str):
            json_string = json.loads(json_string)
        return cls(**json_string)

    def __init__(self, can_answer, can_ask, can_withdraw, until_date=''):
        self.until_date: str = until_date
        self.can_answer: bool = can_answer
        self.can_ask: bool = can_ask
        self.can_withdraw: bool = can_withdraw


class UserSetting(DeJson):
    @classmethod
    def de_json(cls, json_string):
        if isinstance(json_string, str):
            json_string = json.loads(json_string)
        return cls(**json_string)

    def __init__(self, **kwargs):
        self.setting: dict = kwargs
