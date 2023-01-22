try:
    from psycopgን2 import connect
    imported = True

except ImportError:
    from sqlite3 import connect
    imported = False

from util_bot import User, Question, Answer, Setting
import os


def connection():
    if imported:
        conn = connect(host=os.getenv('host'), database=os.getenv('db'), user=os.getenv('user'),
                       port=int(os.getenv('port')), password=os.getenv('pwd'))
    else:
        conn = connect('users_data.db')

    #conn.autocommit = True
    return conn


class Database:
    def __init__(self, deeplink: str):
        self.deeplink = deeplink

    @classmethod
    def update_query(cls, query, *args):
        conn = connection()
        cnx = conn.cursor()
        cnx.execute(query, args)
        conn.commit()
        conn.close()

    @classmethod
    def select_query(cls, query, *args):
        conn = connection()
        cnx = conn.cursor()
        cnx.execute(query, args)
        return cnx
    
    #@classmethod
    def user(self, user_id):
        collection = self.select_query("SELECT * FROM users WHERE user_id %s", user_id).fetchone()
        q = self.select_query("SELECT count(asker) FROM questions WHERE asker %s", user_id).fetchone()
        a = self.select_query("SELECT count(user_id) FROM answers WHERE user_id %s", user_id).fetchone()
        keys = ['name', 'user_id', 'date', 'lang_code', 'balance',
                'username', 'bio', 'invites', 'status', 'link', 'gender', 'setting', 'withdraw', 'phone_number',
                'deeplink']
        if collection is None:
            obj = {k: None for k in keys}
        else:
            obj = dict(zip(keys, collection))
        obj['questions'] = q[0]
        obj['answers'] = a[0]
        obj['deeplink'] = self.deeplink
        return User.de_json(obj)

    def questions(self, user_id, start_from=0):
        collection = self.select_query("SELECT * FROM questions WHERE asker %s", user_id).fetchall()
        keys = ['asker', 'question_id', 'question', 'status', 'date', 'message_id', 'browse', 'unique_link',
                'subject', 'reply', 'browse_link']

        for col in collection[start_from:]:
            obj = dict(zip(keys, col))
            obj['asker'] = self.user(user_id)
            yield Question.de_json(obj)

    def answers(self, question_id, index=0):
        collection = self.select_query("SELECT * FROM answers WHERE question_id %s AND status = 'posted'",
                                       question_id).fetchall()
        keys = ['user_id', 'answer_id', 'question_id', 'date', 'status', 'unique_link', 'reply_to', 'answer',
                'message_id']

        for col in collection[index:]:
            obj = dict(zip(keys, col))
            obj['user_id'] = self.user(obj['user_id']).user_id
            yield Answer.de_json(obj)

    @classmethod
    def is_new(cls, user_id):
        user = cls.select_query("SELECT name FROM users WHERE user_id %s", user_id).fetchone()
        return not isinstance(user, tuple)
        
    @classmethod
    def lang_code(cls, user_id):
        code = cls.select_query("SELECT lang_code FROM users WHERE user_id %s", user_id).fetchone() or [None]
        return code[0]

    def start_message(self) -> str:
        text: str = self.select_query("SELECT start_msg FROM bot").fetchone()
        return ''.join(text)

    @property
    def users(self):
        for xi in self.select_query("SELECT user_id FROM users").fetchall():
            for i in xi:
                yield i

    @property
    def users_link(self):
        for links in self.select_query("SELECT link FROM users").fetchall():
            for link in links:
                yield link

    @property
    def questions_link(self):
        for links in self.select_query("SELECT unique_link FROM questions").fetchall():
            for link in links:
                yield link

    @property
    def browse_link(self):
        for links in self.select_query("SELECT browse_link FROM questions").fetchall():
            for link in links:
                yield link

    @property
    def answers_link(self):
        for links in self.select_query("SELECT unique_link FROM answers").fetchall():
            for link in links:
                yield link

    @property
    def get_setting(self):
        setting = self.select_query("SELECT * FROM setting").fetchone()
        keys = ['admins', 'restriction']
        obj = dict(zip(keys, setting))
        return Setting.de_json(obj)

    def save_question(self, *, asker, question, unique_link, subject, browse):
        import time, json
        question = json.dumps(question)
        date = time.time()
        self.update_query("INSERT INTO questions(asker, question, date, unique_link, subject, browse_link) "
                          "VALUES(?, ?, ?, ?, ?, ?)", asker, question, date, unique_link, subject, browse)

    def save_answer(self, *, user_id, answer, unique_link, question_id, reply_to):
        import time, json
        answer = json.dumps(answer)
        date = time.time()
        self.update_query("INSERT INTO answers(user_id, answer, date, unique_link, question_id, reply_to) "
                          "VALUES(?, ?, ?, ?, ?,?)", user_id, answer, date, unique_link, question_id, reply_to)

    @property
    def max_answer_id(self):
        max_id = self.select_query("SELECT max(answer_id) FROM answers").fetchone()
        return max_id[0] or 0

    def user_max_answer_id(self, user_id):
        max_id = self.select_query("SELECT max(answer_id) FROM answer WHERE user_id %s", user_id).fetchone()
        return max_id[0] or 0

    @property
    def max_question_id(self):
        max_id = self.select_query("SELECT max(question_id) FROM questions").fetchone()
        return max_id[0] or 0

    def user_max_question_id(self, user_id):
        max_id = self.select_query("SELECT max(question_id) FROM questions WHERE asker %s", user_id).fetchone()
        return max_id[0] or 0

    def question(self, question_id):
        collection = self.select_query("SELECT * FROM questions WHERE question_id %s", question_id).fetchone()
        keys = ['asker', 'question_id', 'question', 'status', 'date', 'message_id', 'browse', 'unique_link',
                'subject', 'reply', 'browse_link']
        if not collection:
            obj = {k: None for k in keys}
        else:
            obj = dict(zip(keys, collection))
        return Question.de_json(obj)

    def answer(self, answer_id):
        collection = self.select_query("SELECT * FROM answers WHERE answer_id %s", answer_id).fetchone()
        keys = ['user_id', 'answer_id', 'question_id', 'date', 'status', 'unique_link', 'reply_to', 'answer',
                'message_id']
        if not collection:
            obj = {k: None for k in keys}
        else:
            obj = dict(zip(keys, collection))
        return Answer.de_json(obj)

    def update_balance(self, user_id, balance):
        self.update_query("UPDATE users SET balance = balance + ? WHERE user_id %s", balance, user_id)

    def user_setting(self, user_id):
        user = self.select_query("SELECT setting FROM users WHERE user_id %s", user_id).fetchone()
        if user is None:
            return {}
        elif isinstance(user[0], str):
            import json
            return json.loads(user[0])
        else:
            return user[0]
            
    @classmethod
    @property
    def admins(self) -> dict:
        admin = self.select_query("SELECT admins FROM setting").fetchone()[0]
        if isinstance(admin, str):
            import json
            admin = json.loads(admin)

        return admin
