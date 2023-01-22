import json
from telebot import apihelper, TeleBot, types, util
import threading
import sched

import re
import os
from typing import Union
from telebot.apihelper import ApiTelegramException
from telebot.custom_filters import StateFilter, ChatFilter
from filter import LangCode, Deeplink, NoState, IsAdmin
from keyboard import *
from text import *
from database import Database
from convertor import Convertor
from flask import Flask, request
import time
import hashlib
apihelper.ENABLE_MIDDLEWARE = True

TOKEN = os.getenv("TOKEN")
bot = TeleBot(TOKEN, parse_mode='html', num_threads=10)
app = Flask(__name__)
DEEPLINK = 'http://t.me/{0}?start='.format(bot.get_me().username)
WEBHOOK_URL = os.getenv("URL")
db = Database(DEEPLINK)
OWNER_ID = 5213764043
MAINTAIN = False
PENDING = False
CHANNEL_ID = -1001811307596
INVITATION = .5
markups = {}


@bot.middleware_handler(update_types=['message'])
def get_update(bot_instance, update: Union[types.Update, types.Message]):
    user_id = update.from_user.id
    if update.chat.type == 'private':
        user = db.user(user_id)
        if user.status == 'banned':
            update.content_type = 'banned'
        
        elif MAINTAIN:
            update.content_type = 'maintain'
            
        elif not db.is_new(user_id) and not check_join(user_id) and user.lang_code is not None:
            update.content_type = 'not_join'


def check_join(user_id: int):
    try:
        user = bot.get_chat_member(CHANNEL_ID, user_id)
        return user.status in ['creator', 'administrator', 'member']
    except ApiTelegramException as err:
        if 'chat not found' in err.description:
            return True
        
        return False
        

@bot.message_handler(content_types=['not_join'])
def not_joined(message: types.Message):
    user = message.from_user
    username = bot.get_chat(CHANNEL_ID).username
    btn = InlineKeyboardMarkup([[InlineKeyboardButton('Join', f't.me/{username}')]])
    bot.send_message(user.id,  f'''<b>Dear {user.first_name}</b>
• You need to join our channel with the button below to keep using this bot 😊.''',  reply_markup=btn)


@bot.message_handler(content_types=['banned'])
def banned(message):
    user_id = message.from_user.id
    bot.send_message(user_id, '<b>Sorry you are banned from using this bot. Please contact admin for more.</b>')
    

@bot.message_handler(content_types=["maintain"])
def maintain(message: types.Message):
    bot.send_message(message.from_user.id, "📌 The bot is being maintained and upgraded to serve you better. Please try again later. We will be back soon!")
    
    
@bot.message_handler(commands=['start'], chat_types=['private'], is_deeplink=False)
def start_message(message: types.Message):
    user_id = message.chat.id
    if db.is_new(user_id):
        link = hashlib.sha224(str(user_id).encode('utf-8')).hexdigest()
        if user_id == OWNER_ID:
            status = 'owner'

        else:
            status = 'member'

        db.update_query("INSERT INTO users(user_id, date, link, status) VALUES(?, ?, ?, ?)",
                            *(user_id, time.time(), link, status))
        return bot.send_message(user_id, "<i>Select your langauge / ቋንቋ ይምረጡ</i>", reply_markup=lang_button(True))

    user = db.user(user_id)
    admins = db.admins
    if user.lang_code == 'en':
        text = en_start_message
        btn = main_button(user_id, **admins)
    elif user.lang_code == "am":
        text = am_start_message
        btn = main_button(user_id, **admins)
        
    else:
        text = "<i>Select your langauge / ቋንቋ ይምረጡ</i>"
        btn = lang_button()
    bot.send_message(user_id, text, reply_markup=btn)
    bot.delete_state(user_id)


@bot.message_handler(commands=['start'], is_deeplink=True, chat_types=['private'])
def __start(message: types.Message):
    user_id = message.chat.id
    text = message.text.split()[-1]
    questions_link = [*db.questions_link]
    answers_link = [*db.answers_link]
    browse_link = [*db.browse_link]
    users_link = [*db.users_link]
    user = db.user(user_id)
    if db.is_new(user_id) and not db.is_new(text):
        db.update_query("INSERT INTO invites VALUES(?, ?)", text, user_id)
        db.update_query("UPDATE users SET invites = invites + 1 WHERE user_id = %s", text)
        db.update_balance(text, INVITATION)
        start_message(message)

    elif text in users_link and not db.is_new(user_id) and user.lang_code is not None:

        user = db.user(db.select_query("SELECT user_id FROM users WHERE link = %s", text).fetchone()[0])

        if user.user_id == user_id:
            if user.lang_code == 'en':
                message.text = "👤 Profile"
                en_button(message)

            else:
                message.text = "👤 መግለጫ"
                am_button(message)

        else: 
            bot.send_message(user_id, profile_text.format(user.name, user.gender, user.username, user.count_question, 
                                                                user.count_answers, user.bio, user.date),
                            reply_markup=on_user_profile(user, db.user(user_id), **db.admins))

    elif text in browse_link and not db.is_new(user_id) and user.lang_code is not None:
        question_id = db.select_query("SELECT question_id FROM questions WHERE browse_link = %s", text).fetchone()[0]
        question = db.question(question_id)
        user = db.user(question.asker)
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("Answer", callback_data=f'answer:{question.question_id}')]])

        if question.question['content_type'] == 'text':
            text = f"#{question.subject}\n\n<b>{question.question['text']}</b>\n\nBy: {user.mention}"
            bot.send_message(user_id, text, reply_markup=btn)

        else:
            send_media = getattr(bot, f"send_{question.question['content_type']}")
            text = f"#{question.subject}\n\n<b>{question.question['caption']}</b>\n\nBy: {user.mention}"
            send_media(user_id, question.question[question.question['content_type']], caption=text, reply_markup=btn)

        show_answers(user_id, question_id)

    elif text in answers_link and not db.is_new(user_id) and user.lang_code is not None:
        answer_id = db.select_query("SELECT answer_id FROM answers WHERE unique_link = %s", text).fetchone()[0]
        answer = db.answer(answer_id)
        question = db.question(answer.question_id)
        user = db.user(answer.user_id)
        btn = InlineKeyboardMarkup([[InlineKeyboardButton(f"Browse({question.browse})",      
                                                        callback_data=f'browse_answer:{question.question_id}'),
                                    InlineKeyboardButton("Answer", callback_data=f'answer:{question.question_id}')]])

        if question.question['content_type'] == 'text':
            text = f"#{question.subject}\n\n<b>{question.question['text']}</b>\n\nBy: {user.mention}\n{answer.date}"
            bot.send_message(user_id, text, reply_markup=btn)

        else:
            send_media = getattr(bot, f"send_{question.question['content_type']}")
            text = f"#{question.subject}\n\n<b>{question.question['caption']}</b>\n\nBy: {user.mention}\n{answer.date}"
            send_media(user_id, question.question[question.question['content_type']], caption=text, reply_markup=btn)

        if answer.answer['content_type'] == 'text':
            text = f"<b>{answer.answer['text']}</b>\n\nBy: {user.mention}"
            bot.send_message(user_id, text, reply_markup=on_user_profile(user, db.user(OWNER_ID)))

        else:
            send_media = getattr(bot, f"send_{answer.answer['content_type']}")
            text = f"<b>{answer.answer['caption']}</b>\n\nBy: {user.mention}"
            send_media(user_id, answer.answer[answer.answer['content_type']], caption=text,
                       reply_markup=on_user_profile(user, db.user(OWNER_ID)))

    elif text in questions_link and not db.is_new(user_id) and user.lang_code is not None:
        question_id = db.select_query("SELECT question_id FROM questions WHERE unique_link = %s", text).fetchone()[0]
        question = db.question(question_id)
        user = db.user(question.asker)
        btn = InlineKeyboardMarkup([[InlineKeyboardButton(f"Browse({question.browse})",      
                                    callback_data=f'browse_answer:{question_id}')]])
        if question.question['content_type'] == 'text':
            text = f"#{question.subject}\n\n<b>{question.question['text']}</b>\n\nBy: {user.mention}\n\n"
            bot.send_message(user_id, text, reply_markup=btn)

        else:
            send_media = getattr(bot, f"send_{question.question['content_type']}")
            text = f"#{question.subject}\n\n<b>{question.question['caption']}</b>\n\nBy: {user.mention}\n\n"
            send_media(user_id, question.question[question.question['content_type']], caption=text, reply_markup=btn)

        bot.send_message(user_id, answer_text, reply_markup=cancel(user.lang_code))
        bot.set_state(user_id, "get_answer")
        with bot.retrieve_data(user_id) as data:
            data['question_id'] = question_id

    else:
        start_message(message)


def parse_text_to_user(text: str, user):

    txt = {'{name}': user.name, '{mention}': user.mention, '{user_id}': user.user_id, '{date}': user.date,
           '{balance}': user.balance}

    for old, new in txt.items():
        text = text.replace(old, new)

    return text


@bot.callback_query_handler(lambda call: call.data.startswith('lang'))
def update_lang(call: types.CallbackQuery):
    bot.answer_callback_query(call.id, "Loading....")
    user_id = call.message.chat.id
    code = call.data.split(":")[-1]
    if code.endswith('f'):
        code = code.removesuffix('f')

        if code == 'en':
            text = en_start_message
        else:
            text = am_start_message

        bot.delete_message(user_id, call.message.message_id)
        admins = db.admins
        bot.send_message(user_id, text, reply_markup=main_button(user_id, **admins))

        db.update_query("UPDATE users SET lang_code = %s WHERE user_id = %s", code, user_id)

    else:
        db.update_query("UPDATE users SET lang_code = %s WHERE user_id = %s", code, user_id)
        send_menu(user_id)


@bot.message_handler(func=lambda message: message.text in main_text_en, lang_code='en', no_state=True, chat_types=['private'])
def en_button(message: types.Message):
    user_id = message.chat.id
    text = message.text
    user = db.user(user_id)

    if text == "📝 Ask Question":
        if is_restricted(user_id, 'can_ask'):
            return no_question(user_id)

        else:
            bot.send_message(user_id, question_text, reply_markup=cancel('en'))
            bot.set_state(user_id, UserState.get_question)

    elif text == "🔅 My Questions":
        show_user_questions(user_id)

    elif text == "👤 Profile":
        bot.send_message(user_id, profile_text.format(user.name, user.gender, user.username, user.count_question,
                                                      user.count_answers, user.bio, user.date),
                         reply_markup=user_button())

    elif text == "🧧 Invite":
        bot.send_message(user_id, en_invite_message.format(user.invites, user.balance, user.withdraw, INVITATION,
                                                           f"{DEEPLINK}{user_id}"),
                         reply_markup=invitation_button('en', f"{DEEPLINK}{user_id}"))

    elif text == "🌐 Language":
        bot.send_message(user_id, "<i>Select your langauge / ቋንቋ ይምረጡ</i>", reply_markup=lang_button())

    elif text == "💭 Feedback":
        bot.send_message(user_id, "Send us your feedback with text", reply_markup=cancel("en"))
        bot.set_state(user_id, 'feedback')

    elif text == "📃 Rules":
        rules = open("enrules.txt")
        bot.send_message(user_id, rules.read())
        rules.close()

    elif text == '🎈 Contact':
        bot.send_message(user_id, "<b>✔ Contact the developer\n\n👨‍💻 @Natiprado</b>")


@bot.message_handler(func=lambda message: message.text in main_text_am, lang_code='am', no_state=True, chat_types=['private'])
def am_button(message: types.Message):
    user_id = message.chat.id
    text = message.text
    user = db.user(user_id)

    if text == "📝 ጠይቅ":
        if is_restricted(user_id, 'can_ask'):
            return no_question(user_id)

        else:
            bot.send_message(user_id, question_text, reply_markup=cancel('am'))
            bot.set_state(user_id, UserState.get_question)

    elif text == "🔅 የኔ ጥያቄዎች":
        show_user_questions(user_id)

    elif text == "👤 መግለጫ":
        user = db.user(user_id)
        bot.send_message(user_id, profile_text.format(user.name, user.gender, user.username, user.count_question,
                                                      user.count_answers, user.bio, user.date),
                         reply_markup=user_button())

    elif text == "🧧 ጋብዝ":
        bot.send_message(user_id, am_invite_message.format(user.invites, user.balance, user.withdraw, INVITATION,
                                                           f"{DEEPLINK}{user_id}"),
                         reply_markup=invitation_button('am', f"{DEEPLINK}{user_id}"))

    elif text == "🌐 ቋንቋ":
        bot.send_message(user_id, "<i>Select your langauge / ቋንቋ ይምረጡ</i>", reply_markup=lang_button())

    elif text == "💭 አስታየት":
        bot.send_message(user_id, "ያሎትን አስታየት በጽሑፍ ያድርሱን።", reply_markup=cancel("am"))
        bot.set_state(user_id, 'feedback')
        
    elif text == "📃 ህግጋት":
        rules = open("amrules.txt")
        bot.send_message(user_id, rules.read())
        rules.close()

    elif text == "🎈 አግኝ":
        bot.send_message(user_id, "<b>✔ የቦቱን መስራች ያግኙ\n\n👨‍💻 @Natiprado</b>")
    
    
@bot.callback_query_handler(lambda call: call.data == "ask_question")
def ask_question(call: types.CallbackQuery):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    user = db.user(call.message.chat.id)
    if user.lang_code == "en":
        call.message.text = "📝 Ask Question"
        en_button(call.message)
    else:
        call.message.text = "📝 ጠይቅ"
        am_button(call.message)
    

@bot.message_handler(func=lambda msg: msg.text == "❌ Cancel", lang_code="en", no_state=False, chat_types=['private'])
def en_cancel(message: types.Message):
    user_id = message.chat.id
    state = bot.get_state(user_id)
    user = db.user(user_id)
    if state in ["edit_question", "edit_subject"]:
        with bot.retrieve_data(user_id) as data:
            question_id = data["question_id"]
            send_question(user_id, question_id)
    
    elif state in ["edit_name", "edit_bio", "edit_username"]:
        bot.send_message(user_id, profile_text.format(user.name, user.gender, user.username, user.count_question,
                                                      user.count_answers, user.bio, user.date),
                         reply_markup=user_button())
    
    elif state == 'edit_answer':
        with bot.retrieve_data(user_id) as data:
            answer_id = data['answer_id']
            msg_id = data['message_id']
        answer = db.answer(answer_id)
        if answer.answer['content_type'] == 'text':
            text = f"<b>{answer.answer['text']}</b>\n\nBy: {user.mention}"
            bot.send_message(user_id, text, reply_markup=on_answer_button(answer_id, msg_id))

        else:
            send_media = getattr(bot, f"send_{answer.answer['content_type']}")
            text = f"<b>{answer.answer['caption']}</b>\n\nBy: {user.mention}"
            send_media(user_id, answer.answer[answer.answer['content_type']], caption=text,
                       reply_markup=on_answer_button(answer_id, msg_id))

    bot.delete_state(user_id)
    send_menu(user_id)


@bot.message_handler(func=lambda msg: msg.text == "❌ ሰርዝ", lang_code="am", no_state=False, chat_types=['private'])
def am_cancel(message: types.Message):
    user_id = message.from_user.id
    state = bot.get_state(user_id)
    user = db.user(user_id)
    if state in ["edit_question", "edit_subject"]:
        with bot.retrieve_data(user_id) as data:
            question_id = data["question_id"]
            send_question(user_id, question_id)
    
    elif state in ["edit_name", "edit_bio", "edit_username"]:

        bot.send_message(user_id, profile_text.format(user.name, user.gender, user.username, user.count_question,
                                                      user.count_answers, user.bio, user.date),
                         reply_markup=user_button())
                                
    elif state == 'edit_answer':
        with bot.retrieve_data(user_id) as data:
            answer_id = data['answer_id']
            msg_id = data['message_id']
        send_answer(user_id, answer_id, msg_id)

    bot.delete_state(user_id)
    return send_menu(user_id)

      
@bot.message_handler(func=lambda message: message.text in ["📝 Send Message", "⚙️ Setting", "❔ Questions"],
                     chat_types=['private'], is_admin=True)
def admin_buttons(message: types.Message):
    user_id = message.chat.id
    user = db.user(user_id)
    admins = db.admins
    if message.text == '📝 Send Message':
        if user_id == OWNER_ID or admins[str(user_id)].get('can_send'):
            bot.send_message(user_id, """✳️Enter New Message.\n\nYou can also «Forward» text from another chat or channel.
                                """, reply_markup=cancel(user.lang_code))
            bot.set_state(user_id, 'message')
            markups.clear()

    elif message.text == "❔ Questions":
        if user_id == OWNER_ID or admins[str(user_id)].get('can_approve'):
            questions = db.select_query("SELECT question_id FROM questions WHERE status = 'pending'").fetchall()
            showed = False
            if not PENDING:
                for question_id in questions:
                    question = db.question(question_id[0])
                    btn = InlineKeyboardMarkup()
                    btn.add(InlineKeyboardButton("✔️ Approve", callback_data=f"approve:{question.question_id}"),
                            InlineKeyboardButton("✖️ Decline", callback_data=f"decline:{question.question_id}"))
                    user = db.user(question.asker)
                    if question.question['content_type'] == 'text':
                        text = f"#{question.subject}\n\n<b>{question.question['text']}</b>\n\nBy: {user.mention}"
                        bot.send_message(user_id, text, reply_markup=btn)

                    else:
                        send_media = getattr(bot, f"send_{question.question['content_type']}")
                        text = f"#{question.subject}\n\n<b>{question.question['caption']}</b>\n\nBy: {user.mention}\n\n"
                        send_media(user_id, question.question[question.question['content_type']], caption=text,
                                   reply_markup=btn)
                    showed = True
                if not showed:
                    bot.send_message(user_id, "There are no asked questions")
            else:
                bot.send_message(user_id, "There are no asked questions")
                
    else:
        if user_id == OWNER_ID:
            until = db.get_setting.restriction.until_date    
            bot.send_message(user_id, f"⚙ <i>Chose setting you want to manage</i>\n\n<b>Restriction duration:</b> "
                                      f"<code>{until}</code>", reply_markup=setting_button())


@bot.message_handler(state='message', content_types=util.content_type_media, chat_types=['private'])
def got_message(message: types.Message):
    user_id = message.chat.id
    msg_id = message.message_id
    btn = InlineKeyboardMarkup(row_width=2)
    btn.add(
        types.InlineKeyboardButton("➕ Add", callback_data=f'sm:add'),
        types.InlineKeyboardButton("☑ Done", callback_data=f'sm:done'),
        types.InlineKeyboardButton("🗑 Delete", callback_data='sm:del')
    )
    bot.delete_state(user_id)
    bot.copy_message(user_id, user_id, msg_id, reply_markup=btn)
    send_menu(user_id)


@bot.callback_query_handler(func=lambda call: re.match('^sm', call.data))
def on_got_message(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    data = call.data.split(':')[-1]
    user_id = call.message.chat.id
    user = db.user(user_id)
    if data == 'add':
        bot.send_message(call.message.chat.id, "Send your button text and url link like this:\ntext -> www.text.com",
                         reply_markup=cancel(user.lang_code))
        bot.set_state(user_id, 'add_btn')
        with bot.retrieve_data(user_id) as data:
            data["msg_id"] = call.message.message_id

    elif data == 'del':
        bot.answer_callback_query(call.id, "Message deleted!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_menu(user_id)
        bot.delete_state(user_id)
    else:
        bot.answer_callback_query(call.id, "Sending.......", show_alert=True)
        bot.delete_state(user_id)
        bot.edit_message_reply_markup(user_id, call.message.message_id)
        send_menu(user_id)                 
        send_to_users(call.message)
        

@bot.message_handler(state='add_btn')
def on_send_btn(msg: types.Message):
    text = msg.text
    match = re.findall(r".+\s*->\s*.+", text)
    with bot.retrieve_data(msg.chat.id) as data:
        msg_id = data['msg_id']
    if match:
        btns = {k.split('->')[0]: k.split('->')[1] for k in match}
        for k, v in btns.items():
            markups[k] = {'url': v.lstrip()}
        try:
            del markups["➕ Add"], markups["☑ Done"], markups['🗑 Delete']
        except (IndexError, KeyError):
            pass

        try:
            markups["➕ Add"] = {'callback_data': f'sm:add'}
            markups["☑ Done"] = {'callback_data': f'sm:done'}
            markups["🗑 Delete"] = {'callback_data': 'sm:del'}
            bot.copy_message(msg.chat.id, msg.chat.id, msg_id, reply_markup=util.quick_markup(markups))
        except ApiTelegramException:
            for bt in btns:del markups[bt]
            bot.reply_to(msg, "❌ Invalid Url link ...")
            bot.copy_message(msg.chat.id, msg.chat.id, msg_id, reply_markup=util.quick_markup(markups))
    else:
        markups["➕ Add"] = {'callback_data': f'sm:add'}
        markups["☑ Done"] = {'callback_data': f'sm:done'}
        markups["🗑 Delete"] = {'callback_data': 'sm:del'}
        bot.reply_to(msg, "❌ Error typing...")
        bot.copy_message(msg.chat.id, msg.chat.id, msg_id, reply_markup=util.quick_markup(markups))
    bot.delete_state(msg.chat.id)
    send_menu(msg.chat.id)
  
    
def send_to_users(message: types.Message):
    try:
        del markups["➕ Add"], markups["☑ Done"], markups['🗑 Delete']
    except (IndexError, KeyError):
        pass
    for user_id in db.users:
        try:
            bot.copy_message(user_id, message.chat.id, message.message_id, reply_markup=util.quick_markup(markups))
        except: continue
    markups.clear()
    
    
def is_restricted(user_id, restriction_type):
    setting = db.get_setting.restriction
    user = db.user(user_id)
    if user.status == 'restricted':
        attr = getattr(setting, restriction_type)
        return not attr
    return False


def send_menu(user_id):
    lang_code = db.user(user_id).lang_code
    admins = db.admins
    if lang_code == 'en':
        bot.send_message(user_id, "🏠 Main menu", reply_markup=main_button(user_id, **admins))

    elif lang_code == "am":
        bot.send_message(user_id, "🏠 ዋና ገጽ", reply_markup=main_button(user_id, **admins))
    else:
        bot.send_message(user_id, "<i>Select your langauge / ቋንቋ ይምረጡ</i>", reply_markup=lang_button())

        
@bot.callback_query_handler(lambda call: re.search(r"^(approve|decline)", call.data))
def approve_questions(call: types.CallbackQuery):
    global PENDING
    if PENDING:
        return bot.answer_callback_query(call.id, 'Please try again after some seconds...')
    PENDING = True
    user_id = call.message.chat.id
    question_id = call.data.split(":")[-1] 
    msg_id = call.message.message_id
    question = db.question(question_id)
    admins = db.admins 
    content = call.data.split(":")[0]
    user = db.user(user_id)
    
    if user.status != "owner" and not admins.get(str(user_id), {}).get("can_approve"):
        bot.edit_message_reply_markup(user_id, msg_id)
        return bot.answer_callback_query(call.id, "Sorry you cannot approve or decline this question", show_alert=True)
        
    if question.status != "pending":
        bot.edit_message_reply_markup(user_id, msg_id)
        return bot.answer_callback_query(call.id, "This question cannot be approved or declined", show_alert=True)
    else:
        if content == "decline":
            bot.answer_callback_query(call.id)
            bot.send_message(user_id, "Send the reason why do you decline this question",
                             reply_markup=cancel(user.lang_code))
            bot.set_state(user_id, "decline")
            PENDING = True
            with bot.retrieve_data(user_id) as data:
                data["question_id"] = question.question_id
        else:
            try:
                nq = db.question(question_id)
                if nq.status != 'pending':
                    bot.answer_callback_query(call.id, "This question cannot approve!!")
                    return bot.edit_message_reply_markup(user_id, msg_id)

                btn = InlineKeyboardMarkup([[InlineKeyboardButton("Answer", DEEPLINK+question.unique_link),
                                             InlineKeyboardButton(f"Browse({question.browse})", DEEPLINK+question.browse_link)]])
                msg = bot.copy_message(CHANNEL_ID, user_id, msg_id, reply_markup=btn)
                db.update_query("UPDATE questions SET status = 'approved' WHERE question_id = %s", question.question_id)
                db.update_query("UPDATE questions SET message_id = %s WHERE question_id = %s", msg.message_id, question.question_id)
                bot.answer_callback_query(call.id, "Question is approved!")
                bot.edit_message_reply_markup(user_id, msg_id)
                try:
                    btn = InlineKeyboardMarkup([[InlineKeyboardButton("Show me", f"t.me/{bot.get_chat(CHANNEL_ID).username}/{msg.message_id}")]])
                    bot.send_message(question.asker, "Your question is approved!", reply_markup=btn)
                except:
                    pass
            except:
                bot.answer_callback_query(call.id, "Bot is not admin on the channel!")
            PENDING = False
                

@bot.message_handler(state="decline")
def decline_question(message: types.Message):
    global PENDING
    user_id = message.chat.id
    with bot.retrieve_data(user_id) as data:
        question_id = data["question_id"]
    db.update_query("UPDATE questions SET status = 'declined' WHERE question_id = %s", question_id)
    question = db.question(question_id)
    try:
        bot.send_message(question.asker, f"Your question is declined!\n\n<b>Reason:</b> {message.text}")
    except ApiTelegramException:pass
    bot.send_message(user_id, "Declined!")
    send_menu(user_id)
    bot.delete_state(user_id)
    PENDING = False


@bot.callback_query_handler(lambda call: call.data.startswith("setting"))
def bot_setting(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    if call.data.endswith("res"):
        bot.edit_message_reply_markup(OWNER_ID, call.message.message_id)
        bot.send_message(OWNER_ID, "Enter value", reply_markup=cancel(db.user(OWNER_ID).lang_code))
        bot.set_state(OWNER_ID, "duration")
    else:
        text = "<b>👑 Bot admins</b>\n\n"
        count = 1
        for admin in db.admins:
            text += f"<i>#{count}</i>. {db.user(admin).mention}\n\n"
            count+=1
        bot.edit_message_text(text, OWNER_ID, call.message.message_id, reply_markup=bot_admins_button())
    

@bot.message_handler(state="duration")
def get_duration(message: types.Message):
    text = message.text
    regex = re.search('(^\d+)\s+(year|month|hour|day|min|sec)s?', text, re.I)
    if regex:
        setting = db.select_query("SELECT restriction FROM setting").fetchone()[0]
        if isinstance(setting, str):
            setting = json.loads(setting)
        setting["until_date"] = regex.group().lower()
        db.update_query("UPDATE setting SET restriction = %s", json.dumps(setting))
        message.text = "⚙️ Setting"
        admin_buttons(message)
        bot.delete_state(OWNER_ID)
        send_menu(OWNER_ID)
    else:
        bot.send_message(OWNER_ID, "Invalid!\n\nPlease use only min, sec, hour, day, year, month")
        
        
@bot.callback_query_handler(lambda call: call.data.startswith("admin"))
def on_bot_admins(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    msg_id = call.message.message_id
    content = call.data.split(":")[-1]
    if content == "back":
        text = "<b>👑 Bot admins</b>\n\n"
        count = 1
        for admin in db.admins:
            text += f"<i>#{count}</i>. {db.user(admin).mention}\n\n"
            count +=1
        bot.edit_message_text(text, OWNER_ID, msg_id, reply_markup=bot_admins_button())
    elif content == "add":
        bot.edit_message_reply_markup(OWNER_ID,msg_id)
        bot.send_message(OWNER_ID, "Forward any message from user you want to add as an admin.",
                         reply_markup=cancel(db.user(OWNER_ID).lang_code))
        bot.set_state(OWNER_ID, "add_admin")
    else:
        user = db.user(int(content))
        if user.status == "admin":
            the_admin = db.admins[str(user.user_id)]
            pr = ["✅" if the_admin[k] else "❌" for k in the_admin]
            bot.edit_message_text(admin_text.format(user.mention, *pr), OWNER_ID, msg_id,
                                  reply_markup=admin_permission(user.user_id, **the_admin))
        else:
            bot.edit_message_reply_markup(OWNER_ID, msg_id, reply_markup=bot_admins_button())
    

@bot.message_handler(state="add_admin", content_types=util.content_type_media)
def add_admin(message: types.Message):
    forward_from = message.forward_from
    if forward_from:
        user = db.user(forward_from.id)
        if user.status in ["admin", "owner"]:
            bot.send_message(OWNER_ID, "This user is already admin.\n\nForward any message from you want to add"
                                       " as an admin")
        elif user.status is None:
            bot.send_message(OWNER_ID, "This user is not a member of this bot.\n\nFoward any message from you want "
                                       "to add as an admin.")
        else:
            bot.send_message(OWNER_ID, "✅ Admin added successfully.")
            admins = db.admins
            admins[user.user_id] = {"can_ban": False, "can_approve": True, "can_restrict": False, "can_send": False,
                                    "can_see": False}
            db.update_query("UPDATE setting SET admins = %s", json.dumps(admins))
            db.update_query("UPDATE users SET status = 'admin' WHERE user_id = %s", user.user_id)
            text = "<b>👑 Bot admins</b>\n\n"
            count = 1
            for admin in db.admins:
                text += f"<i>#{count}</i>. {db.user(admin).mention}\n\n"
                count+=1
            bot.send_message(OWNER_ID, text, reply_markup=bot_admins_button())
            send_menu(OWNER_ID)
            bot.delete_state(OWNER_ID)
    else:
        bot.send_message(OWNER_ID, "Invalid foward!\n\nFoward any message from you want to add as an admin.")
        

@bot.callback_query_handler(lambda call: re.search("bot_admin", call.data))   
def manage_admin_permission(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    content = call.data.split(":")[1]
    user_id = call.data.split(":")[-1]
    
    user = db.user(user_id)
    
    if user.status != "admin" or content == "back":
        call.data = "admin:back"
        on_bot_admins(call)
    
    elif content == "remove":
        admins = db.admins
        del admins[user_id]
        db.update_query("UPDATE users SET status = 'member' WHERE user_id = %s", user_id)
        db.update_query("UPDATE setting SET admins = %s", json.dumps(admins))
        call.data = "admin:back"
        on_bot_admins(call)
        
    else:
        admin = db.admins[user_id]
        admins = db.admins
        if admin[f"can_{content}"]:
            admin[f"can_{content}"] = False
        else:
            admin[f"can_{content}"] = True
        admins[user_id] = admin
        db.update_query("UPDATE setting SET admins = %s", json.dumps(admins))
        call.data = f"admin:{user_id}"
        on_bot_admins(call)
        
        
class UserState:
    get_question = 'get_question'
    get_subject = 'get_subject'


@bot.message_handler(state=UserState.get_question, content_types=['text', 'audio', 'animation', 'document',
                                                                  'photo', 'video', 'voice'])
def get_question(message: types.Message):
    user_id = message.chat.id
    if is_restricted(user_id, 'can_ask'):
        return no_question(user_id)

    content_type = message.content_type
    file_id = ''
    if not message.text:
        if message.caption is None:
            return bot.send_message(user_id, '<code>The document must have a caption(text under document). '
                                             'please send with a caption or send only text.</code>')

        else:
            bot.send_message(user_id, "<i>Chose a subject for your question...</i>", reply_markup=subject_button())
            file = getattr(message, content_type)
            if content_type != 'photo':
                file_id = file.file_id
            else:
                file_id = file[-1].file_id

    else:
        bot.send_message(user_id, "<code>Chose a subject for your question...</code>", reply_markup=subject_button())
    bot.set_state(user_id, UserState.get_subject)
    question = {'content_type': content_type, content_type: file_id or util.escape(message.text),
                'caption': '' if not message.caption else util.escape(message.caption)}
    with bot.retrieve_data(user_id) as data:
        data['question'] = question


@bot.message_handler(state=UserState.get_subject)
def get_subject(message: types.Message):
    user_id = message.chat.id
    text = message.text

    if is_restricted(user_id, 'can_ask'):
        return no_question(user_id)

    if text not in subject_text:
        bot.send_message(user_id, "<i>Chose subject of your question...</i>", reply_markup=subject_button())

    else:
        subject = text[2:].strip().replace(" ", "_").lower()
        if subject == "አማርኛ":
            subject = 'amharic'

        with bot.retrieve_data(user_id) as data:
            question = data['question']

        link = hashlib.sha256(str(db.max_question_id + 1).encode('utf-8')).hexdigest()
        browse = hashlib.sha224(str(db.max_question_id+1).encode('utf-8')).hexdigest()
        db.save_question(asker=user_id, question=question, subject=subject, unique_link=link, browse=browse)
        send_question(user_id, db.user_max_question_id(user_id))
        send_menu(user_id)
        return bot.delete_state(user_id)


@bot.callback_query_handler(lambda call: re.search(r'edit:(subject|question|enable|disable)', call.data))
def __edit_question(call: types.CallbackQuery):
    user_id = call.message.chat.id
    msg_id = call.message.message_id
    question_id = int(call.data.split(":")[-1])
    content = call.data.split(':')[-2]
    question = db.question(question_id)
    bot.edit_message_reply_markup(user_id, msg_id)

    if question.status is None:
        return bot.send_message(user_id, "This question is no longer available")

    elif question.status != 'previewing':
        return bot.answer_callback_query(call.id, "This question cannot be edited", show_alert=True)

    if is_restricted(user_id, 'can_ask'):
        return no_question(user_id)

    if content == 'question':
        bot.answer_callback_query(call.id)
        bot.send_message(user_id, question_text, reply_markup=cancel(db.lang_code(user_id)))
        state = 'edit_question'

    elif content == 'subject':
        bot.answer_callback_query(call.id)
        bot.send_message(user_id, "<i>Select subject of question</i>", reply_markup=subject_button())
        state = 'edit_subject'

    elif content == 'enable':
        bot.answer_callback_query(call.id, "Reply enabled.\n\nEveryone can reply to other answers that has been "
                                           "answered to your question including you.", show_alert=True)

        db.update_query("UPDATE questions set reply = true WHERE question_id = %s", question_id)
        bot.edit_message_reply_markup(user_id, msg_id, reply_markup=on_question_button(question_id, True))
        return

    else:
        bot.answer_callback_query(call.id, "Reply disabled.\n\nNobody can reply to other answers that has been "
                                           "answered to your question, but you can reply.", show_alert=True)

        db.update_query("UPDATE questions set reply = false WHERE question_id = %s", question_id)
        bot.edit_message_reply_markup(user_id, msg_id, reply_markup=on_question_button(question_id, False))
        return

    bot.set_state(user_id, state)
    with bot.retrieve_data(user_id) as data:
        data['question_id'] = question_id


@bot.message_handler(state='edit_question', content_types=['text', 'audio', 'animation', 'document',
                                                           'photo', 'video', 'voice'])
def edit_question(message: types.Message):
    user_id = message.chat.id
    with bot.retrieve_data(user_id) as data:
        question_id = data['question_id']

    if is_restricted(user_id, 'can_ask'):
        return no_question(user_id)

    content_type = message.content_type
    question = db.question(question_id)
    if not message.text:
        if message.caption is None:
            return bot.send_message(user_id, '<code>The document must have a caption(text under document). '
                                             'please send with a caption or send only text.</code>')

        else:
            file = getattr(message, content_type)
            if content_type != 'photo':
                file_id = file.file_id

            else:
                file_id = file[-1].file_id

        question.question['caption'] = util.escape(message.caption)

    else:
        file_id = util.escape(message.text)

    question_content = question.question['content_type']
    del question.question[question_content]
    question.question[content_type] = file_id
    question.question['content_type'] = content_type
    db.update_query('UPDATE questions SET question = %s WHERE question_id = %s', json.dumps(question.question), question_id)
    send_question(user_id, question_id)
    send_menu(user_id)
    return bot.delete_state(user_id)


@bot.message_handler(state='edit_subject')
def edit_subject(message: types.Message):
    user_id = message.chat.id

    with bot.retrieve_data(user_id) as data:
        question_id = data['question_id']

    if is_restricted(user_id, 'can_ask'):
        return no_question(user_id)

    text = message.text
    if text not in subject_text:
        bot.send_message(user_id, "<i>Chose subject of your question...</i>", reply_markup=subject_button())

    else:
        subject = text[2:].strip().replace(" ", "_").lower()
        if subject == "አማርኛ":
            subject = 'amharic'

        db.update_query("UPDATE questions SET subject = %s WHERE question_id = %s", subject, question_id)
        send_question(user_id, question_id)
        send_menu(user_id)
        return bot.delete_state(user_id)


def no_question(user_id):
    until = db.user(user_id).setting.setting['until_date']
    if db.lang_code(user_id) == 'en':
        bot.send_message(user_id, f"❌ Sorry you cannot ask any question until <b>{until}.</b>")

    else:
        bot.send_message(user_id, f"❌ ይቅርታ እስከ <b>{until}</b> ድረስ ምንም አይነት ጥያቄ መጠየቅ አይችሉም ።")
    send_menu(user_id)
    return bot.delete_state(user_id)


def no_answer(user_id):
    until = db.user(user_id).setting.setting['until_date']
    if db.lang_code(user_id) == 'en':
        bot.send_message(user_id, f"❌ Sorry you cannot answer any question until <b>{until}.</b>")

    else:
        bot.send_message(user_id, f"❌ ይቅርታ እስከ <b>{until}</b> ድርስ ምንም አይነት ጥያቄ መመለስ አይችሉም።")
    send_menu(user_id)
    return bot.delete_state(user_id)


def send_question(user_id, question_id):
    new_question = db.question(question_id)
    user = db.user(user_id)
    if new_question.question['content_type'] == 'text':
        text = f"#{new_question.subject}\n\n<b>{new_question.question['text']}</b>\n\nBy: {user.mention}\n\n"\
        f"Status: <code>{new_question.status}</code>"
        bot.send_message(user_id, text, reply_markup=on_question_button(question_id, new_question.reply))

    else:
        send_media = getattr(bot, f"send_{new_question.question['content_type']}")
        text = f"#{new_question.subject}\n\n<b>{new_question.question['caption']}</b>\n\nBy: {user.mention}\n\n" \
        f"Status: <code>{new_question.status}</code>"
        send_media(user_id, new_question.question[new_question.question['content_type']], caption=text,
                   reply_markup=on_question_button(question_id, new_question.reply))


@bot.callback_query_handler(lambda call: re.search(r'cancel_question', call.data))
def cancel_question(call: types.CallbackQuery):
    user_id = call.message.chat.id
    message_id = call.message.message_id
    question_id = int(call.data.split(":")[-1])
    question = db.question(question_id)

    if question.status in ['pending',  'previewing']:
        bot.answer_callback_query(call.id, "Canceled...")
        content_type = call.message.content_type
        user = db.user(user_id)
        db.update_query("UPDATE questions SET status = 'canceled' WHERE question_id = %s", question_id)
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("☑ Re submit", callback_data=f'submit:{question_id}')]])
        
        if content_type == 'text':
            text = f"#{question.subject}\n\n<b>{question.question['text']}</b>\n\nBy: {user.mention}\n\n" \
                   f"Status: <code>canceled</code>"
            bot.edit_message_text(text, user_id, message_id, reply_markup=btn)

        else:
            text = f"#{question.subject}\n\n<b>{question.question['caption']}</b>\n\nBy: {user.mention}\n\n" \
                   f"Status: <code>canceled</code>"
            bot.edit_message_caption(text, user_id, message_id, reply_markup=btn)

    else:
        bot.edit_message_reply_markup(user_id, message_id)
        bot.answer_callback_query(call.id, "This question cannot be canceled.", show_alert=True)


@bot.callback_query_handler(lambda call: call.data.startswith('submit'))
def submit_question(call: types.CallbackQuery):
    user_id = call.message.chat.id
    question_id = int(call.data.split(":")[-1])
    question = db.question(question_id)
    msg_id = call.message.message_id

    if question.status in ['previewing', 'canceled']:
        bot.answer_callback_query(call.id, "Your question is submitted")
        content_type = call.message.content_type
        user = db.user(user_id)
        btn = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f'cancel_question:{question_id}')]])
        
        if content_type == 'text':
            text = f"#{question.subject}\n\n<b>{question.question['text']}</b>\n\nBy: {user.mention}\n\n" \
            f"Status: <code>pending</code>"
            bot.edit_message_text(text, user_id, msg_id, reply_markup=btn)

        else:
            text = f"#{question.subject}\n\n<b>{question.question['caption']}</b>\n\nBy: {user.mention}\n\n" \
            f"Status: <code>pending</code>"
            bot.edit_message_caption(text, user_id, msg_id, reply_markup=btn)

        db.update_query("UPDATE questions SET status = 'pending' WHERE question_id = %s", question_id)

    else:
        bot.edit_message_reply_markup(user_id, msg_id)
        bot.answer_callback_query(call.id, f"This question cannot be submitted. It is already {question.status}", True)


@bot.callback_query_handler(lambda call: call.data.startswith('edit_user'))
def edit_user(call: types.CallbackQuery):
    user_id = call.message.chat.id
    message_id = call.message.message_id
    content = call.data.split(":")[-1]
    user = db.user(user_id)
    
    if content == 'name':
        bot.edit_message_reply_markup(user_id, message_id)
        bot.send_message(user_id, "Enter your name\n\n<code>Note that your name can only contain latters, numbers and"
                                  " underscore. And must be less than 20 character</code>",
                         reply_markup=cancel(user.lang_code))
        bot.set_state(user_id, 'edit_name')

    elif content == 'username':
        bot.edit_message_reply_markup(user_id, message_id)
        bot.send_message(user_id, "Enter your username\n\n<code>Note that your username\n\n"
                                  "1 Can only contain latter, numbers and underscore.\n\n"
                                  "2 Minimum character is 5 and Maximum character is 25.\n\n"
                                  "3 Must be unique and start with \"$\" sign.</code>",
                         reply_markup=cancel(user.lang_code))

        bot.set_state(user_id, 'edit_username')

    elif content == 'bio':
        bot.edit_message_reply_markup(user_id, message_id)
        bot.send_message(user_id, "Write a few words about yourself.\n\n<code>Note that maximum character is 80</code>",
                         reply_markup=cancel(user.lang_code))
        bot.set_state(user_id, 'edit_bio')

    elif content == 'gender':
        gender = user.gender
        bot.edit_message_text("Select your gender", user_id, message_id, reply_markup=user_gender_button(gender))

    bot.answer_callback_query(call.id)


@bot.message_handler(state='edit_name')
def edit_name(message: types.Message):
    user_id = message.chat.id
    text = message.text
    regex = re.fullmatch(r"\w{,20}", text)
    user = db.user(user_id)
    if regex:
        name = regex.group()
        db.update_query("UPDATE users SET name = %s WHERE user_id = %s", name, user_id)
        
        if user.lang_code == 'en':
            message.text = "👤 Profile"
            en_button(message)

        else:
            message.text = '👤 መግለጫ'
            am_button(message)
            
        send_menu(user_id)
        bot.delete_state(user_id)

    else:
        bot.send_message(user_id, "Enter your name\n\n<code>Note that your name can only contain latter, numbers and"
                                  " underscore. And must be less than 20 character</code>")


@bot.message_handler(state='edit_username')
def edit_username(message: types.Message):
    user_id = message.chat.id
    text = message.text
    
    regex = re.fullmatch(r"^\$\w{,25}", text)

    user = db.user(user_id)
    if regex:
        username = regex.group()
        usernames = db.select_query("SELECT username FROM users").fetchall()

        for names in usernames:
            if names[0] is None: continue

            r2 = re.fullmatch(fr"\{username}", names[0], re.I)
            if r2:
                bot.send_message(user_id, "This username is already taken.\n\nEnter username")
                break

        else:
            db.update_query("UPDATE users SET username = %s WHERE user_id = %s", username, user_id)
            
            if user.lang_code == 'en':
                message.text = "👤 Profile"
                en_button(message)

            else:
                message.text = '👤 መግለጫ'
                am_button(message)

            send_menu(user_id)
            bot.delete_state(user_id)

    else:
        bot.send_message(user_id, "Enter your username\n\n<code>Note that your username\n\n"
                                  "1 Can only contain latter, numbers and underscore.\n\n"
                                  "2 Minimum character is 5 and Maximum character is 25.\n\n"
                                  "3 Must be unique and start with \"$\" sign.</code>")


@bot.message_handler(state='edit_bio')
def edit_bio(message: types.Message):
    user_id = message.chat.id
    text = message.text
    user = db.user(user_id)

    if len(text) < 80:
        bio = util.escape(text)
        db.update_query("UPDATE users SET bio = %s WHERE user_id = %s", bio, user_id)
        
        if user.lang_code == 'en':
            message.text = "👤 Profile"
            en_button(message)

        else:
            message.text = '👤 መግለጫ'
            am_button(message)

        send_menu(user_id)
        bot.delete_state(user_id)

    else:
        bot.send_message(user_id, "Write a few words about yourself.\n\n<code>Note that maximum character is 80</code>")


@bot.callback_query_handler(lambda call: call.data.startswith("gender"))
def edit_gender(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    user_id = call.message.chat.id
    message_id = call.message.message_id

    user = db.user(user_id)
    try:
        content = call.data.split(":")[-1]
        if content == 'back':
            bot.edit_message_text(profile_text.format(user.name, user.gender, user.username, user.count_question,
                                                      user.count_answers, user.bio, user.date), user_id, message_id,
                                  reply_markup=user_button())

        else:
            if content == 'custom':
                gender = ''

            else:
                gender = content

            db.update_query("UPDATE users SET gender = %s WHERE user_id = %s", gender, user_id)
            bot.edit_message_reply_markup(user_id, message_id, reply_markup=user_gender_button(gender))

    except ApiTelegramException:
        pass


@bot.callback_query_handler(lambda call: re.search(r'inv:', call.data))
def on_inv(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    user_id = call.message.chat.id
    message_id = call.message.message_id
    user = db.user(user_id)
    content = call.data.split(":")[-1]

    if content == "withdraw":
        if is_restricted(user_id, 'can_withdraw'):
            until = user.setting.setting['until']
            return bot.send_message(user_id, f"Sorry you are restricted until {until}",)

        if user.lang_code == 'en':
            text = "How much birr do you want to withdraw?"

        else:
            text = "ምን ያህል ብር ወጪ ማድረግ ይፈልጋሉ ?"

        bot.edit_message_text(text, user_id, message_id, reply_markup=withdraw_button(user.lang_code))

    else:
        invites = db.select_query("SELECT invited_user FROM invites WHERE invited_by = %s LIMIT 10", user_id).fetchall()
        text, count = '<b>የጋበዟቸው ሰዎች</b>\n\n', 1

        for inv in invites:
            text += f"{count} - <a href='tg://user?id={inv[0]}'>{inv[0]}</a>\n\n"
            count+=1
        bot.edit_message_text(text, user_id, message_id, reply_markup=user_invites(user.invites, 1))


@bot.callback_query_handler(lambda call: call.data.startswith('withdraw'))
def withdraw_money(call: types.CallbackQuery):
    user_id = call.message.chat.id
    message_id = call.message.message_id
    user = db.user(user_id)
    content = call.data.split(":")[-1]

    if content == 'back':
        bot.answer_callback_query(call.id)

        if user.lang_code == 'en':
            text = en_invite_message

        else:
            text = am_invite_message

        bot.edit_message_text(text.format(user.invites, user.balance, user.withdraw, INVITATION, f"{DEEPLINK}{user_id}"),
                              user_id,  message_id, reply_markup=invitation_button(user.lang_code, f"{DEEPLINK}{user_id}"))

    else:
        if is_restricted(user_id, 'can_withdraw'):
            until = user.setting.setting['until']
            return bot.send_message(user_id, f"Sorry you are restricted until {until}",)

        money = int(content)
        if money <= user.balance:
            if user.phone_number is not None:
                bot.answer_callback_query(call.id, "Processing.....")
                bt = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back" if user.lang_code == 'en' else "🔙 ተመለስ",
                                                                 callback_data='withdraw:back')]])
                bot.edit_message_text("Your withdraw request is sent to the admin, so you will get your money in 24 "
                                      "hours and you will be notified when it is done.", user_id, message_id,
                                      reply_markup=bt)

                db.update_balance(user_id, -money)
                db.update_query("UPDATE users SET withdraw = withdraw + ? WHERE user_id = %s", money, user_id)
                send_menu(user_id)
                mention = f"<a href='tg://user?id={call.message.chat.id}'>{call.message.chat.id}</a>"
                btn = InlineKeyboardMarkup([[InlineKeyboardButton("✔ Sent", callback_data=f'sent:{user_id}:{money}')]])
                bot.send_message(OWNER_ID, f'• <b>Withdraw request</b>\n\n👤 From: {mention}\n<b>💵 Amount</b>: {money} ETB'
                                           f'<b>📱 Phone</b>: <code>{user.phone_number}</code>', reply_markup=btn)

            else:
                btn = ReplyKeyboardMarkup(resize_keyboard=True)
                btn.add(KeyboardButton("📱 Share Phone", request_contact=True))
                bot.edit_message_reply_markup(user_id, message_id)
                msg = bot.send_message(user_id, "Please send us your phone number using bellow button", reply_markup=btn)
                bot.register_next_step_handler(msg, get_phone)

        else:
            bot.answer_callback_query(call.id, "You don't have sufficient balance!")


def get_phone(message: types.Message):
    user_id = message.chat.id
    user = db.user(user_id)

    if message.contact is None:
        msg = bot.send_message(user_id, "Please send us your phone number using bellow button")
        bot.register_next_step_handler(msg, get_phone)

    elif not message.reply_to_message:
        msg = bot.send_message(user_id, "Please send us your phone number using bellow button")
        bot.register_next_step_handler(msg, get_phone)

    elif message.contact.first_name != message.from_user.first_name:
        msg = bot.send_message(user_id, "Please send us your phone number using bellow button")
        bot.register_next_step_handler(msg, get_phone)

    else:
        regex = re.search(r'^\+?2519\d{8}', message.contact.phone_number)
        if not regex:
            btn = types.ReplyKeyboardRemove()
            return bot.send_message(user_id, "That is invalid phone number", reply_markup=btn)

        else:
            db.update_query("UPDATE users SET phone_number = %s WHERE user_id = %s", message.contact.phone_number, user_id)

        if user.lang_code == 'en':
            text = "How much birr do you want to withdraw?"

        else:
            text = "ምን ያህል ብር ወጪ ማድረግ ይፈልጋሉ ?"

        bot.send_message(user_id, text, reply_markup=withdraw_button(user.lang_code))
        send_menu(user_id)
        bot.clear_step_handler_by_chat_id(user_id)


@bot.callback_query_handler(lambda call: call.data.startswith('invite'))
def on_my_invites(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    user_id = call.message.chat.id
    message_id = call.message.message_id
    user = db.user(user_id)
    content = call.data.split(":")[-1]

    if content == 'menu':
        if user.lang_code == 'en':
            text = en_invite_message

        else:
            text = am_invite_message

        bot.edit_message_text(text.format(user.invites, user.balance, user.withdraw, INVITATION, f"{DEEPLINK}{user_id}"),
                              user_id,  message_id, reply_markup=invitation_button(user.lang_code, f"{DEEPLINK}{user_id}"))


    else:
        row = int(content)
        invites = db.select_query("SELECT invited_user FROM invites WHERE invited_by = %s", user_id).fetchall()
        text, count = '<b>የጋበዟቸው ሰዎች</b>\n\n', 1

        for inv in range(row*10-9, row*10+1):
            try:
                text += f"{count+(row*10-9)} - <a href='tg://user?id={invites[inv][0]}'>{invites[inv][0]}</a>\n\n"
                count+=1
            except IndexError:
                break

        bot.edit_message_text(text, user_id, message_id, reply_markup=user_invites(user.invites, row))


@bot.callback_query_handler(lambda call: call.data.startswith('sent'))
def send_confirmation(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    user_id = int(call.data.split(":")[1])
    amount = call.data.split(":")[-1]
    bot.send_message(OWNER_ID, "Send confirmation photo")
    bot.set_state(OWNER_ID, 'send')
    with bot.retrieve_data(OWNER_ID) as data:
        data['user_id'] = user_id
        data['message_id'] = call.message.message_id
        data['amount'] = amount


@bot.message_handler(state='send', content_types=['photo'])
def send(message: types.Message):
    photo = message.photo[-1].file_id
    
    with bot.retrieve_data(OWNER_ID) as data:
        user_id = data['user_id']
        message_id = data['message_id']
        amount = data['amount']

    bot.edit_message_reply_markup(OWNER_ID, message_id)
    bot.send_message(OWNER_ID, "Done", reply_to_message_id=message_id)
    bot.send_photo(user_id, photo, caption=f"Your <b>{amount} Birr</b> withdrawal is done.")
    send_menu(OWNER_ID)
    bot.delete_state(OWNER_ID)


@bot.callback_query_handler(lambda call: call.data.startswith('report'))
def report_answer(call: types.CallbackQuery):
    bot.answer_callback_query(call.id, 'Report sent!')
    user_id = call.from_user.id
    ans_id = call.data.split(":")[-1]
    link = db.answer(ans_id).unique_link
    bot.send_message(OWNER_ID, f"<a href='{DEEPLINK+link}'>One question is reported</a>\nBy: {db.user(user_id).mention}")
    
    
@bot.callback_query_handler(lambda call: re.search(r"my_(all|more)_question", call.data))
def show_more_user_question(call: types.CallbackQuery):
    bot.answer_callback_query(call.id, "Loading your questions....")
    user_id = call.message.chat.id
    message_id = call.message.message_id
    index = int(call.data.split(":")[-1])

    bot.edit_message_text("🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨", user_id, message_id)

    if call.data.startswith("my_all"):
        show_user_questions(user_id, index, True)

    else:
        show_user_questions(user_id, index)


@bot.callback_query_handler(lambda call: re.search(r"all_answer|more_answer", call.data))
def show_more_answers(call: types.CallbackQuery):
    bot.answer_callback_query(call.id, "Loading answers....")
    user_id = call.message.chat.id
    message_id = call.message.message_id
    index = int(call.data.split(":")[-1])
    question_id = int(call.data.split(":")[1])
    bot.edit_message_text("🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨", user_id, message_id)

    if call.data.startswith("all_answer"):
        show_answers(user_id, question_id, index, True)

    else:
        show_answers(user_id, question_id, index)


def show_user_questions(user_id, index=0, show_all=False):
    showed = False
    user = db.user(user_id)
    count = 0
    for new_question in db.questions(user_id, index):
        try:
            if not show_all and count == 10:
                break
            status = new_question.status
            
            question_id = new_question.question_id

            if status == 'previewing':
                btn = on_question_button(question_id, new_question.reply)

            elif status == 'canceled':
                btn = InlineKeyboardMarkup([[InlineKeyboardButton("☑ Re submit", callback_data=f'submit:{question_id}')]])

            elif status == 'approved':
                btn = InlineKeyboardMarkup([[InlineKeyboardButton(f"Browse({new_question.browse})",
                                                                  callback_data=f'browse_answer:{question_id}'),
                                             InlineKeyboardButton("Answer", callback_data=f"answer:{question_id}")]])
            elif status == 'pending':
                btn = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f'cancel_question:{question_id}')]])

            else:
                btn = None

            if new_question.question['content_type'] == 'text':
                text = f"#{new_question.subject}\n\n<b>{new_question.question['text']}</b>\n\nBy: {user.mention}\n\n" \
                f"Status: <code>{new_question.status}</code>"
                bot.send_message(user_id, text, reply_markup=btn)

            else:
                send_media = getattr(bot, f"send_{new_question.question['content_type']}")
                text = f"#{new_question.subject}\n\n<b>{new_question.question['caption']}</b>\n\nBy: {user.mention}\n\n"\
                f"Status: <code>{new_question.status}</code>"
                send_media(user_id, new_question.question[new_question.question['content_type']], caption=text,
                           reply_markup=btn)
           
            count += 1
            showed = True

        except: continue

    lang = user.lang_code
    index += count

    if not showed:
        ask_q = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("Ask" if lang == 'en' else 'ጠይቅ', callback_data='ask_question')
        ask_q.add(btn)

        if lang == 'en':
            bot.send_message(user_id, "Sorry you don't have any asked question yet.", reply_markup=ask_q)

        elif lang == 'am':
            bot.send_message(user_id, "ይቅርታ እስካሁን ምንም የጠየቁት ጥያቄ የለም ።", reply_markup=ask_q)

    else:
        text = f'Showed - {index}, Total - {user.count_question}' if user.lang_code == 'en' else f"የታየ - {index} ፣ አጠቃላይ - {user.count_question}"
        if user.count_question > index:
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("Show more" if user.lang_code == 'en' else "ተጨማሪ አሳይ"
                                                              , callback_data=f'my_more_question:{index}'),
                                         InlineKeyboardButton("Show all" if user.lang_code == 'en' else "ሁሉንም አሳይ",
                                                              callback_data=f'my_all_question:{index}')]],
                                       row_width=1)

        else:
            btn = None

        bot.send_message(user_id, text, reply_markup=btn)


answers_json = {}


def show_answers(user_id, question_id, index=0, show_all=False):
    global answers_json
    answers = db.answers(question_id, index)
    count = 0
    showed = False
    me = db.user(user_id)
    question = db.question(question_id)

    for answer in answers:
        try:
            if not show_all and count == 10:
                break
            
            user = db.user(answer.user_id)
            asker = "#asker" if answer.user_id == question.asker else ""
            btn = InlineKeyboardMarkup()
            ls = []

            if question.reply or user_id == question.asker:
                ls.append(InlineKeyboardButton("↪ Reply", callback_data=f'reply_answer:{answer.answer_id}'))

            ls.append(InlineKeyboardButton("⚠ Report", callback_data=f'report_answer:{answer.answer_id}'))
            btn.add(*ls)

            if answer.answer['content_type'] == 'text':
                text = f"{asker}\n\n<b>{answer.answer['text']}</b>\n\nBy: {user.mention}\n{answer.date}"
                msg = bot.send_message(user_id, text.strip(), reply_markup=btn,
                                       reply_to_message_id=answers_json.get(user_id, {}).get(answer.reply_to))


            else:
                send_media = getattr(bot, f"send_{answer.answer['content_type']}")
                text = f"{asker}\n\n<b>{answer.answer['caption']}</b>\n\nBy: {user.mention}\n{answer.date}"
                msg = send_media(user_id, answer.answer[answer.answer['content_type']], caption=text.strip(),
                                 reply_markup=btn, reply_to_message_id=answers_json.get(user_id, {}).get(answer.reply_to))

            count += 1
            showed = True

            js = answers_json.get(user_id, {})
            js[answer.answer_id] = msg.message_id
            answers_json[user_id] = js
            
        except: continue

    index += count

    if showed:
        text = f'Showed - {index}, Total - {question.browse}' if me.lang_code == 'en' else f"የታየ - {index} ፣ አጠቃላይ - {question.browse}"
        if question.browse > index:
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("Show more" if me.lang_code == 'en' else "ተጨማሪ አሳይ",
                                                              callback_data=f'more_answer:{question_id}:{index}'),
                                         InlineKeyboardButton("Show all" if me.lang_code == 'en' else "ሁሉንም አሳይ",
                                                              callback_data=f'all_answer:{question_id}:{index}')]],
                                       row_width=1)
        else:
            btn = None

        bot.send_message(user_id, text, reply_markup=btn)

    else:
        bot.send_message(user_id, "Be the first to answer this question.")


@bot.message_handler(state='get_answer', content_types=['text', 'audio', 'animation', 'document',
                                                        'photo', 'video', 'voice'])
def get_answer(message: types.Message):
    user_id = message.chat.id
    user = db.user(user_id)

    if is_restricted(user_id, 'can_answer'):
        return no_question(user_id)

    with bot.retrieve_data(user_id) as data:
        question_id = data['question_id']
        reply_to = data.get('reply_to', 0)
        msg_id = data.get('message_id', 0)
   
    content_type = message.content_type
    file_id = ''

    if not message.text:
        if message.caption is None:
            return bot.send_message(user_id, '<code>The document must have a caption(text under document). '
                                             'please send with a caption or send only text.</code>')

        else:
            file = getattr(message, content_type)
            if content_type != 'photo':
                file_id = file.file_id

            else:
                file_id = file[-1].file_id

    answer = {'content_type': content_type, content_type: file_id or util.escape(message.text),
              'caption': '' if not message.caption else util.escape(message.caption)}
    link = hashlib.sha1(str(db.max_answer_id+1).encode("utf-8")).hexdigest()
    
    db.save_answer(user_id=user_id, answer=answer, unique_link=link, question_id=question_id, reply_to=reply_to)
    send_answer(user_id, db.max_answer_id, msg_id)
    bot.delete_state(user_id)
    send_menu(user_id)


@bot.callback_query_handler(lambda call: re.search(r'edit:answer', call.data))
def edit_answer(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    user_id = call.message.chat.id
    message_id = call.message.message_id
    answer_id, msg_id = call.data.split(':')[2:]
    answer = db.answer(answer_id)
    bot.edit_message_reply_markup(user_id, message_id)
    
    if answer.status != 'previewing':
        return bot.send_message(user_id, "This answer cannot be edited!")

    else:
        text =  answer_text.replace("answer", "reply") if answer.reply_to else answer_text
        bot.send_message(user_id, text, reply_markup=cancel(db.user(user_id).lang_code))
        bot.set_state(user_id, 'edit_answer')

        with bot.retrieve_data(user_id) as data:
            data['answer_id'] = answer_id
            data['message_id'] = msg_id


@bot.message_handler(state='edit_answer', content_types=['text', 'audio', 'animation', 'document',
                                                         'photo', 'video', 'voice'])
def edit_answer(message: types.Message):
    user_id = message.chat.id
    user = db.user(user_id)

    with bot.retrieve_data(user_id) as data:
        answer_id = data['answer_id']
        message_id = data.get('message_id', 0)

    content_type = message.content_type
    file_id = ''

    if not message.text:
        if message.caption is None:
            return bot.send_message(user_id, '<code>The document must have a caption(text under document). '
                                             'please send with a caption or send only text.</code>')

        else:
            file = getattr(message, content_type)
            if content_type != 'photo':
                file_id = file.file_id

            else:
                file_id = file[-1].file_id            

    answer = {'content_type': content_type, content_type: file_id or util.escape(message.text) ,
              'caption': '' if not message.caption else util.escape(message.caption)}
    db.update_query("UPDATE answers SET answer = %s WHERE answer_id = %s", json.dumps(answer), answer_id)
    send_answer(user_id, answer_id, message_id)
    bot.delete_state(user_id)
    send_menu(user_id)


def send_answer(user_id, answer_id, message_id=0):
    reply_to =  db.answer(answer_id).reply_to
    answer =  db.answer(answer_id)
    user = db.user(user_id)
    if reply_to:
        the_answer = db.answer(reply_to)
        
        if the_answer.answer['content_type'] == 'text':
            reply_text = f"↪ <b>In reply to</b>\n<i>\"{the_answer.answer['text']}\"</i>"

        else:
            reply_text = f"↪ <b>In reply to</b>\n<i>\"{the_answer.answer['caption']}\"</i>"

    else:
        reply_text = ''
    
    if answer.answer['content_type'] ==  'text':
        bot.send_message(user_id, f"<b>{answer.answer['text']}</b>\n\nBy: {user.mention}",
                         reply_markup=on_answer_button(answer_id, message_id))
    else:
        send_media = getattr(bot, f'send_{answer.answer["content_type"]}')  
        send_media(user_id, answer.answer[answer.answer['content_type']],
                   caption=f"{reply_text}\n\n<b>{answer.answer['caption']}</b>\n\nBy: {user.mention}".strip(),
                   reply_markup=on_answer_button(answer_id, message_id))
    
    
@bot.callback_query_handler(lambda call: call.data.startswith('post'))
def post_answer(call: types.CallbackQuery):
    user_id = call.message.chat.id
    message_id = call.message.message_id
    answer_id, msg_id = call.data.split(':')[1:]
    answer = db.answer(answer_id)
    user = db.user(user_id)
    question = db.question(answer.question_id)

    if is_restricted(user_id, 'can_answer'):
        bot.answer_callback_query(call.id)
        return no_answer(user_id)

    elif answer.status != 'previewing':
        bot.edit_message_reply_markup(user_id, message_id)
        return bot.send_message(user_id, "This answer cannot be posted!")

    else:
        bot.answer_callback_query(call.id, "Your answer is posted!")
        bot.delete_message(user_id, message_id)
        to_user = question.asker if not answer.reply_to else db.answer(answer.reply_to).user_id
        
        reply_msg_id = None if not answer.reply_to else db.answer(answer.reply_to).message_id
        asker = "#asker" if answer.user_id == question.asker else ""
        btn = InlineKeyboardMarkup()
        ls = []

        if question.reply or user_id == question.asker:
            ls.append(InlineKeyboardButton("↪ Reply", callback_data=f'reply_answer:{answer.answer_id}'))

        ls.append(InlineKeyboardButton("⚠ Report", callback_data=f'report_answer:{answer.answer_id}'))
        btn.add(*ls)
        db.update_query("UPDATE questions SET browse = browse + 1 WHERE question_id = %s", question.question_id)  
        db.update_query("UPDATE answers SET date = %s WHERE answer_id = %s", time.time(), answer_id)   
        db.update_query("UPDATE answers SET status = 'posted' WHERE answer_id = %s", answer_id)
        answer = db.answer(answer_id)
        bt = InlineKeyboardMarkup([[InlineKeyboardButton("Answer", DEEPLINK+question.unique_link),
                                    InlineKeyboardButton(f"Browse({question.browse+1})", DEEPLINK+question.browse_link)]])
        bot.edit_message_reply_markup(CHANNEL_ID, question.message_id, reply_markup=bt)  
                 
        if answer.answer['content_type'] == 'text':
            text = f"{asker}\n\n<b>{answer.answer['text']}</b>\n\nBy: {user.mention}\n{answer.date}".strip()
            msg = bot.send_message(user_id, text.strip(), reply_markup=btn, reply_to_message_id=msg_id)
            db.update_query("UPDATE answers SET message_id = %s WHERE answer_id = %s", msg.message_id, answer_id)
            
            if user_id == to_user:return
            try:
                if to_user == question.asker and not answer.reply_to:
                    url = f't.me/{bot.get_chat(CHANNEL_ID).username}/{question.message_id}'
                    bot.send_message(to_user, f"{user.mention} has answered your <a href='{url}'>question</a>",
                                     disable_web_page_preview=True)
                bot.send_message(to_user, text.strip(), reply_markup=btn, reply_to_message_id=reply_msg_id)

            except ApiTelegramException:
                pass

        else:
            send_media = getattr(bot, f"send_{answer.answer['content_type']}")
            text = f"{asker}\n\n<b>{answer.answer['caption']}</b>\n\nBy: {user.mention}\n{answer.date}"
            msg = send_media(user_id, answer.answer[answer.answer['content_type']], caption=text.strip(),
                             reply_to_message_id=msg_id, reply_markup=btn)
            db.update_query("UPDATE answers SET message_id = %s WHERE answer_id = %s", msg.message_id, answer_id)
            if user_id == to_user:return
            try:
                url = f't.me/{bot.get_chat(CHANNEL_ID).username}/{question.message_id}'
                if to_user == question.asker and not answer.reply_to:
                    bot.send_message(to_user, f"{user.mention} has answered your <a href='{url}'>question</a>",
                                     disable_web_page_preview=True)
                                 
                send_media(to_user, answer.answer[answer.answer['content_type']], caption=text.strip(),  reply_markup=btn,
                           reply_to_message_id=reply_msg_id)

            except ApiTelegramException:
                pass


@bot.callback_query_handler(lambda call: call.data.startswith('browse_answer'))
def browse_answer(call: types.CallbackQuery):
    bot.answer_callback_query(call.id, "Loading....")
    user_id = call.message.chat.id
    question_id = call.data.split(":")[-1]
    show_answers(user_id, question_id)


@bot.callback_query_handler(lambda call: call.data.startswith('answer'))
def answer_to_question(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    user_id = call.message.chat.id
    question_id = int(call.data.split(':')[-1])
    user = db.user(user_id)
    bot.send_message(user_id, answer_text, reply_markup=cancel(user.lang_code))
    bot.set_state(user_id, 'get_answer')

    with bot.retrieve_data(user_id) as data:
        data['question_id'] = question_id


@bot.callback_query_handler(lambda call: call.data.startswith('reply_answer'))
def reply_answer(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    user_id = call.message.chat.id
    user = db.user(user_id)
    answer_id = call.data.split(":")[-1]
    answer = db.answer(answer_id)
    
    if is_restricted(user_id, 'can_answer'):
        return no_answer(user_id)

    bot.send_message(user_id, answer_text.replace("answer", 'reply'), reply_markup=cancel(user.lang_code))
    bot.set_state(user_id, 'get_answer')

    with bot.retrieve_data(user_id) as data:
        data['question_id'] = answer.question_id
        data['reply_to'] = answer_id
        data['message_id'] = call.message.message_id


@bot.callback_query_handler(lambda call: call.data.startswith("user"))
def get_user(call: types.CallbackQuery):
    user_id = call.message.chat.id
    user = db.user(user_id)
    admin = db.admins.get(str(user_id), {})
    content, usr_id = call.data.split(':')[1:]
    msg_id = call.message.message_id

    usr = db.user(usr_id)
    if content == "chat":
        bot.answer_callback_query(call.id)
        bot.send_message(user_id, "<code>Write your message</code>", reply_markup=cancel(user.lang_code))
        bot.set_state(user_id, 'chat')
        with bot.retrieve_data(user_id) as data:
            data['to_user'] = usr_id
           
        return
        
    if user.status != 'owner' and not admin.get(f'can_{user_id}'):
        bot.answer_callback_query(call.id, 'You dont have this permission!')
        return bot.edit_message_reply_markup(user_id, msg_id, reply_markup=on_user_profile(usr, user, **db.admins))
    
    elif user.status == 'admin' and usr.status == 'admin':
        bot.answer_callback_query(call.id, 'This user is admin!')
        return bot.edit_message_reply_markup(user_id, msg_id, reply_markup=on_user_profile(usr, user, **db.admins))
    
    elif usr.status == 'owner':
        bot.answer_callback_query(call.id, 'He is owner')
        return bot.edit_message_reply_markup(user_id, msg_id, reply_markup=on_user_profile(db.user(usr_id), user, **db.admins))
    
    else:
        
        if content == 'ban':
            if usr.status != 'banned':
                bot.answer_callback_query(call.id, 'Banned!')
                db.update_query("UPDATE users SET status = 'banned' WHERE user_id = %s", usr_id)
                bot.ban_chat_member(CHANNEL_ID, usr_id)
            else:
                bot.answer_callback_query(call.id, 'This user is already banned!')
        
        elif content == 'restrict':
            if usr.status in ['member', 'admin']:
                bot.answer_callback_query(call.id, 'Restricted!')
                db.update_query("UPDATE users SET status = 'restricted' WHERE user_id = %s", usr_id)
                dur = db.get_setting.restriction.until_date
                obj = Convertor(dur)
                setting = db.select_query('SELECT setting FROM users WHERE user_id = %s', usr_id).fetchone()[0]
                if isinstance(setting, str):
                    setting = json.loads(setting)
                setting['until_date'] = obj.convert
                db.update_query("UPDATE users SET setting = %s WHERE user_id = %s", json.dumps(setting), usr_id)
                event.enter(obj.second, 1, unrestrict, argument=(usr_id,))
                
            else:
                bot.answer_callback_query(call.id, f'This user is already {usr.status}')
        
        elif content in ['unban', 'unrestrict']:
            if content == 'unban' and usr.status =='banned':
                bot.answer_callback_query(call.id, 'Unbanned!')
                unrestrict(usr_id)
                bot.unban_chat_member(CHANNEL_ID, usr_id)
            elif content == 'unrestrict' and usr.status == 'restricted':
                bot.answer_callback_query(call.id, 'Unrestricted!')
                unrestrict(usr_id)
            else:
                bot.answer_callback_query(call.id, f'This user is already {usr.status}')
        
        elif content == 'send':
            bot.answer_callback_query(call.id)
            bot.send_message(user_id, '<code>Send your message....</code>', reply_markup=cancel(user.lang_code))
            bot.set_state(user_id, 'admin_message')
            with bot.retrieve_data(user_id) as data:
                data['to_user'] = usr_id
            return
        else:
            bot.answer_callback_query(call.id, 'Fetching Information.....')
            mention = f"<a href='tg://user?id={int(usr_id)}'>{int(usr_id)}</a>"
            bot.send_message(user_id, f'<b>Name:</b> {usr.name}\<b>ID:</b> {usr.user_id}\n'
                                      f'<b>Phone:</b> {usr.phone_number}\n\n{mention}')
        return bot.edit_message_reply_markup(user_id, msg_id, reply_markup=on_user_profile(db.user(usr_id), user, **db.admins))


def unrestrict(user_id):
    user = db.user(user_id)
    is_admin = db.admins.get(str(user_id))
    if is_admin:
        status = 'admin'  
    else:
        status = 'member'  
    db.update_query('UPDATE users SET status = %s WHERE user_id = %s', status, user_id)
    
    
@bot.message_handler(state='chat', content_types=util.content_type_media)
def chat(message: types):
    user_id = message.from_user.id
    with bot.retrieve_data(user_id) as data:
        to_user = data['to_user']
    if not message.text:
        bot.send_message(user_id, 'Text is required!')
    else:
        try:
            bot.send_message(to_user, f'<b>{util.escape(message.text)}</b>\n\nBy: {db.user(user_id).mention}',
                                      reply_markup=on_user_profile(db.user(to_user), db.user(user_id), **db.admins))
        except ApiTelegramException:
            pass
        bot.reply_to(message, f'Message is sent to {db.user(to_user).mention}')
        send_menu(user_id)
        bot.delete_state(user_id)
        
        
@bot.message_handler(state='admin_message', content_types=util.content_type_media)
def admin_message(message: types):
    user_id = message.from_user.id
    with bot.retrieve_data(user_id) as data:
        to_user = data['to_user']
    try:
       bot.copy_message(to_user, user_id, message.message_id)
    except ApiTelegramException:
        pass
    bot.reply_to(message, f'Message is sent to {db.user(to_user).mention}')
    send_menu(user_id)
    bot.delete_state(user_id)


@bot.message_handler(state='feedback', content_types=util.content_type_media)
def get_user_feedback(message: types.Message):
    user_id = message.from_user.id
    if not message.text:
        bot.send_message(user_id, 'Text is required!') 
    else:
        bot.send_message(OWNER_ID, f"#Feedback\n<b>{util.escape(message.text)}</b>\n\nBy: {db.user(user_id).mention}", 
                                   reply_markup=on_user_profile(db.user(user_id), db.user(OWNER_ID)))
        if db.user(user_id).lang_code == 'en':
            bot.send_message(user_id, 'Thank you for your feedback!')
        else:
            bot.send_message(user_id, 'እናመሰግናለን!')
        send_menu(user_id)
        bot.delete_state(user_id)
  

@bot.message_handler(commands=['get'], chat_id=[OWNER_ID])
def get(message: types.Message):
    text = message.text.split()
    user = db.user(text[-1])
    if user.status is not None:
        message.text = "/start {}".format(user.link)
        __start(message)
    else:
        bot.reply_to(message, 'This user not a member of this bot')


@bot.message_handler(commands=['off', 'on'], chat_id=[OWNER_ID])
def off(message):
    global PENDING
    if message.text == '/on':
        PENDING = True
    else:
        PENDING = False
    bot.reply_to(message, 'Done!')
    
    
def forever():
    while 1:
        event.run()


@app.route("/")
def index():
    bot.remove_webhook()
    bot.set_webhook(WEBHOOK_URL+"/"+TOKEN)
    return 'Webhook created', 200
    
    
@app.route("/"+TOKEN, methods=['POST'])
def get_updates():
    data = request.get_data().decode("utf-8")
    update = types.Update.de_json(data)
    bot.process_new_updates([update])
    return '!', 200
    

event = sched.scheduler(time.time, time.sleep)
th = threading.Thread(target=forever) 
th.start()   
            
bot.add_custom_filter(LangCode())
bot.add_custom_filter(Deeplink())
bot.add_custom_filter(NoState(bot))
bot.add_custom_filter(StateFilter(bot))
bot.add_custom_filter(IsAdmin())
bot.add_custom_filter(ChatFilter())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)))