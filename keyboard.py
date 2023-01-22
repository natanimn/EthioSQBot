from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def lang_button(first=False):
    lang = InlineKeyboardMarkup([[InlineKeyboardButton('🇬🇧 English', callback_data='lang:en' if not first else 'lang:enf'),
                                  InlineKeyboardButton("🇪🇹 Amharic", callback_data='lang:am' if not first else 'lang:amf')
                                ]])
    return lang


main_text_en = ['📝 Ask Question', '🔅 My Questions', '👤 Profile', '🧧 Invite', '🌐 Language', '💭 Feedback', '📃 Rules',
                '🎈 Contact']

main_text_am = ['📝 ጠይቅ', '🔅 የኔ ጥያቄዎች', '👤 መግለጫ', '🧧 ጋብዝ', '🌐 ቋንቋ', '💭 አስታየት', '📃 ህግጋት', '🎈 አግኝ']


def main_button(user_id, **kwargs):
    from database import Database as db
    user = db("").user(user_id)
    user_id = str(user_id)
    if user.lang_code == 'en':
        k = main_text_en
    else:
        k = main_text_am
    btn = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    ad = []
    if user.status == 'owner' or kwargs.get(user_id,{}).get('can_send'):
        ad.append(KeyboardButton("📝 Send Message"))
    if user.status == "owner" or kwargs.get(user_id, {}).get("can_approve"):
        ad.append(KeyboardButton("❔ Questions"))
    if user.status == "owner":
        ad.append(KeyboardButton("⚙️ Setting"))
        
    btn.add(*ad, row_width=3)

    btn.add(*[KeyboardButton(i) for i in k])

    return btn


def cancel(lang):
    btn = ReplyKeyboardMarkup(resize_keyboard=True)
    btn.add(KeyboardButton("❌ Cancel" if lang == 'en' else "❌ ሰርዝ"))
    return btn


subject_text = ["🇬🇧 English", "🇪🇹 አማርኛ", "🇪🇹 Afaan Oromoo", "🧪 Chemistry", "🧮 Math", "🔭 Physics", "⚽ HPE", "🔬 Biology",
                "💻 ICT", "🌏 History", "🧭 Geography", "⚖ Civics", '✏ TD', "💶 Economics", '💰 Business']


def subject_button():
    btn = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn.add(*subject_text)
    btn.add(KeyboardButton("❌ Cancel"))
    return btn


def on_question_button(question_id, reply=True):
    btn = InlineKeyboardMarkup(row_width=2)
    btn.add(*[InlineKeyboardButton("📝 Edit question", callback_data=f'edit:question:{question_id}'),
              InlineKeyboardButton('📖 Edit Subject', callback_data=f'edit:subject:{question_id}'),
              InlineKeyboardButton("Enable Reply" if not reply else "Disable Reply",
                                   callback_data=f'edit:{"enable" if not reply else "disable"}:{question_id}'),
              InlineKeyboardButton("❌ Cancel", callback_data=f'cancel_question:{question_id}'),
              InlineKeyboardButton('✅ Submit', callback_data=f'submit:{question_id}'),
              ])
    return btn


def user_button():
    btn = InlineKeyboardMarkup(row_width=2)
    btn.add(*[
        InlineKeyboardButton("Edit name", callback_data='edit_user:name'),
        InlineKeyboardButton("Edit username", callback_data='edit_user:username'),
        InlineKeyboardButton("Edit bio", callback_data='edit_user:bio'),
        InlineKeyboardButton("Edit gender", callback_data='edit_user:gender'),
       
    ])
    return btn


def user_gender_button(gender):
    btn = InlineKeyboardMarkup()
    btn.add(*[
        InlineKeyboardButton("Male" if not gender == '👨' else "✅ Male", callback_data='gender:👨'),
        InlineKeyboardButton("Female" if not gender == '👩' else "✅ Female", callback_data='gender:👩'),
        InlineKeyboardButton("Custom" if gender != '' else "✅ Custom", callback_data='gender:custom')
    ])
    btn.add(*[InlineKeyboardButton("🔙 Back", callback_data='gender:back')])
    return btn


def invitation_button(lang, link):
    btn = InlineKeyboardMarkup(row_width=2)
    btn.add(InlineKeyboardButton("💳 Withdraw" if lang == 'en' else "💳 ወጪ አርግ", callback_data='inv:withdraw'),
            InlineKeyboardButton("👥 Stats" if lang == 'en' else "👥 ዝርዝር", callback_data='inv:stats'),
            InlineKeyboardButton("⤴ Share" if lang == 'en' else "⤴ አጋራ", f"t.me/share/url?url={link}"))
    return btn


def withdraw_button(lang):
    btn = InlineKeyboardMarkup(row_width=2)
    ls = [5, 10, 15, 25, 50, 100]
    n = [InlineKeyboardButton(f'{i} {"Birr" if lang == "en" else "ብር"}', callback_data=f'withdraw:{i}') for i in ls]

    btn.add(*n)
    btn.add(InlineKeyboardButton("🔙 Back" if lang == 'en' else "🔙 ተመለስ", callback_data='withdraw:back'))
    return btn


def user_invites(max_row, current_row):
    btn = InlineKeyboardMarkup()

    if max_row > 10:

        if current_row == 1:
            btn.add(InlineKeyboardButton("▶️", callback_data='invite:2'))

        elif current_row*10 >= max_row:
            btn.add(InlineKeyboardButton("◀️", callback_data=f'invite:{current_row-1}'))

        else:
            btn.add(InlineKeyboardButton("◀️", callback_data=f'invite:{current_row-1}'),
                    InlineKeyboardButton("▶️", callback_data=f'invite:{current_row+1}'))
    btn.add(InlineKeyboardButton("🏠 Menu", callback_data='invite:menu'))
    return btn


def on_user_profile(the_user, user, **kwargs):
    btn = InlineKeyboardMarkup()
    ls = []

    def is_owner_or_admin(_user):
        return _user.status in ['admin', 'owner']

    append = False
    if the_user.user_id != user.user_id:
        btn.add(InlineKeyboardButton("📝 Send Message", callback_data=f'user:chat:{the_user.user_id}'))
    if the_user.status == "owner":
        return btn
        
    if user.status == 'owner':
        ls.extend([InlineKeyboardButton("✅ Unban" if the_user.status == 'banned' else "🚷 Ban" ,
                                        callback_data=f'user:{"unban" if the_user.status == "banned" else "ban"}:{the_user.user_id}'),
                   InlineKeyboardButton("✅ Un Restrict" if the_user.status == 'restricted' else "📵 Restrict",
                                        callback_data=f'user:{"unrestrict" if the_user.status == "restricted" else "restrict"}:{the_user.user_id}'),
                   InlineKeyboardButton("👤 Show Profile", callback_data=f'user:show:{the_user.user_id}'),
                   ])
        append = True
    elif user.status == 'admin':
        if kwargs.get(str(user.user_id), {}).get('can_ban'):
            if not is_owner_or_admin(the_user):
                ls.append(InlineKeyboardButton("✅ Unban" if the_user.status == 'banned' else "🚷 Ban",
                                               callback_data=f'user:{"unban" if the_user.status=="banned" else "ban"}:{the_user.user_id}'))
        if kwargs.get(str(user.user_id), {}).get('can_restrict'):
            if not is_owner_or_admin(the_user):
                ls.append(InlineKeyboardButton("✅ Un Restrict" if the_user.status == 'restricted' else "📵 Restrict",
                                               callback_data=f'user:{"unrestrict" if the_user.status == "restricted" else "restrict"}:{the_user.user_id}'))

        if kwargs.get(str(user.user_id), {}).get('can_see'):
           ls.append(InlineKeyboardButton("👤 Show Profile", callback_data=f'user:show:{the_user.user_id}'))

        if kwargs.get(str(user.user_id), {}).get('can_send'):
            if not is_owner_or_admin(the_user):
                append = True
    btn.add(*ls, row_width=2)
    if append:
        btn.add(InlineKeyboardButton("📝 Send message as admin", callback_data=f'user:send:{the_user.user_id}'))
    return btn


def on_answer_button(answer_id, message_id=0):
    btn = InlineKeyboardMarkup()
    btn.add(*[InlineKeyboardButton("📝 Edit answer", callback_data=f'edit:answer:{answer_id}:{message_id}'),
              InlineKeyboardButton('✅ Post', callback_data=f'post:{answer_id}:{message_id}'),
              ])
    return btn


def setting_button():
    btn = InlineKeyboardMarkup(row_width=1)
    btn.add(
    InlineKeyboardButton("🔄 Change Restriction", callback_data="setting:res"),
    InlineKeyboardButton("👑 Admins", callback_data="setting:admins")
    )
    return btn


def bot_admins_button():
    from database import Database as db
    btn = InlineKeyboardMarkup(row_width=2)
    admins = db.admins
    ls = [InlineKeyboardButton(user, callback_data=f"admin:{user}") for user in admins]
    btn.add(*ls)
    btn.add(InlineKeyboardButton("➕ Add Admin", callback_data="admin:add"))
    btn.add(InlineKeyboardButton("🔙 Back", callback_data="admin:back"))
    return btn
    
    
def admin_permission(user_id, **kwargs):
    btn = InlineKeyboardMarkup(row_width=2)
    btn.add(
    InlineKeyboardButton("✅ Ban" if kwargs["can_ban"] else "❌ Ban", callback_data=f"bot_admin:ban:{user_id}"),
    InlineKeyboardButton("✅ Approve" if kwargs["can_approve"] else "❌ Approve", callback_data=f"bot_admin:approve:{user_id}"),
    InlineKeyboardButton("✅ Send" if kwargs["can_send"] else "❌ Send", callback_data=f"bot_admin:send:{user_id}"),    InlineKeyboardButton("✅ Restrict" if kwargs["can_restrict"] else "❌ Restrict", callback_data=f"bot_admin:restrict:{user_id}"),
    InlineKeyboardButton("✅ See profile" if kwargs["can_see"] else "❌ See profile", callback_data=f"bot_admin:see:{user_id}"))
    btn.add(InlineKeyboardButton("➖ Remove", callback_data=f"bot_admin:remove:{user_id}")
    )
    btn.add(InlineKeyboardButton("🔙 Back", callback_data=f"bot_admin:back:{user_id}"))
    
    return btn