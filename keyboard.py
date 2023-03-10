from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def lang_button(first=False):
    lang = InlineKeyboardMarkup([[InlineKeyboardButton('๐ฌ๐ง English', callback_data='lang:en' if not first else 'lang:enf'),
                                  InlineKeyboardButton("๐ช๐น Amharic", callback_data='lang:am' if not first else 'lang:amf')
                                ]])
    return lang


main_text_en = ['๐ Ask Question', '๐ My Questions', '๐ค Profile', '๐งง Invite', '๐ Language', '๐ญ Feedback', '๐ Rules',
                '๐ Contact']

main_text_am = ['๐ แ แญแ', '๐ แจแ แฅแซแแแฝ', '๐ค แแแแซ', '๐งง แแฅแ', '๐ แแแ', '๐ญ แ แตแณแจแต', '๐ แแแแต', '๐ แ แแ']


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
        ad.append(KeyboardButton("๐ Send Message"))
    if user.status == "owner" or kwargs.get(user_id, {}).get("can_approve"):
        ad.append(KeyboardButton("โ Questions"))
    if user.status == "owner":
        ad.append(KeyboardButton("โ๏ธ Setting"))
        
    btn.add(*ad, row_width=3)

    btn.add(*[KeyboardButton(i) for i in k])

    return btn


def cancel(lang):
    btn = ReplyKeyboardMarkup(resize_keyboard=True)
    btn.add(KeyboardButton("โ Cancel" if lang == 'en' else "โ แฐแญแ"))
    return btn


subject_text = ["๐ฌ๐ง English", "๐ช๐น แ แแญแ", "๐ช๐น Afaan Oromoo", "๐งช Chemistry", "๐งฎ Math", "๐ญ Physics", "โฝ HPE", "๐ฌ Biology",
                "๐ป ICT", "๐ History", "๐งญ Geography", "โ Civics", 'โ TD', "๐ถ Economics", '๐ฐ Business']


def subject_button():
    btn = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn.add(*subject_text)
    btn.add(KeyboardButton("โ Cancel"))
    return btn


def on_question_button(question_id, reply=True):
    btn = InlineKeyboardMarkup(row_width=2)
    btn.add(*[InlineKeyboardButton("๐ Edit question", callback_data=f'edit:question:{question_id}'),
              InlineKeyboardButton('๐ Edit Subject', callback_data=f'edit:subject:{question_id}'),
              InlineKeyboardButton("Enable Reply" if not reply else "Disable Reply",
                                   callback_data=f'edit:{"enable" if not reply else "disable"}:{question_id}'),
              InlineKeyboardButton("โ Cancel", callback_data=f'cancel_question:{question_id}'),
              InlineKeyboardButton('โ Submit', callback_data=f'submit:{question_id}'),
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
        InlineKeyboardButton("Male" if not gender == '๐จ' else "โ Male", callback_data='gender:๐จ'),
        InlineKeyboardButton("Female" if not gender == '๐ฉ' else "โ Female", callback_data='gender:๐ฉ'),
        InlineKeyboardButton("Custom" if gender != '' else "โ Custom", callback_data='gender:custom')
    ])
    btn.add(*[InlineKeyboardButton("๐ Back", callback_data='gender:back')])
    return btn


def invitation_button(lang, link):
    btn = InlineKeyboardMarkup(row_width=2)
    btn.add(InlineKeyboardButton("๐ณ Withdraw" if lang == 'en' else "๐ณ แแช แ แญแ", callback_data='inv:withdraw'),
            InlineKeyboardButton("๐ฅ Stats" if lang == 'en' else "๐ฅ แแญแแญ", callback_data='inv:stats'),
            InlineKeyboardButton("โคด Share" if lang == 'en' else "โคด แ แแซ", f"t.me/share/url?url={link}"))
    return btn


def withdraw_button(lang):
    btn = InlineKeyboardMarkup(row_width=2)
    ls = [5, 10, 15, 25, 50, 100]
    n = [InlineKeyboardButton(f'{i} {"Birr" if lang == "en" else "แฅแญ"}', callback_data=f'withdraw:{i}') for i in ls]

    btn.add(*n)
    btn.add(InlineKeyboardButton("๐ Back" if lang == 'en' else "๐ แฐแแแต", callback_data='withdraw:back'))
    return btn


def user_invites(max_row, current_row):
    btn = InlineKeyboardMarkup()

    if max_row > 10:

        if current_row == 1:
            btn.add(InlineKeyboardButton("โถ๏ธ", callback_data='invite:2'))

        elif current_row*10 >= max_row:
            btn.add(InlineKeyboardButton("โ๏ธ", callback_data=f'invite:{current_row-1}'))

        else:
            btn.add(InlineKeyboardButton("โ๏ธ", callback_data=f'invite:{current_row-1}'),
                    InlineKeyboardButton("โถ๏ธ", callback_data=f'invite:{current_row+1}'))
    btn.add(InlineKeyboardButton("๐  Menu", callback_data='invite:menu'))
    return btn


def on_user_profile(the_user, user, **kwargs):
    btn = InlineKeyboardMarkup()
    ls = []

    def is_owner_or_admin(_user):
        return _user.status in ['admin', 'owner']

    append = False
    if the_user.user_id != user.user_id:
        btn.add(InlineKeyboardButton("๐ Send Message", callback_data=f'user:chat:{the_user.user_id}'))
    if the_user.status == "owner":
        return btn
        
    if user.status == 'owner':
        ls.extend([InlineKeyboardButton("โ Unban" if the_user.status == 'banned' else "๐ท Ban" ,
                                        callback_data=f'user:{"unban" if the_user.status == "banned" else "ban"}:{the_user.user_id}'),
                   InlineKeyboardButton("โ Un Restrict" if the_user.status == 'restricted' else "๐ต Restrict",
                                        callback_data=f'user:{"unrestrict" if the_user.status == "restricted" else "restrict"}:{the_user.user_id}'),
                   InlineKeyboardButton("๐ค Show Profile", callback_data=f'user:show:{the_user.user_id}'),
                   ])
        append = True
    elif user.status == 'admin':
        if kwargs.get(str(user.user_id), {}).get('can_ban'):
            if not is_owner_or_admin(the_user):
                ls.append(InlineKeyboardButton("โ Unban" if the_user.status == 'banned' else "๐ท Ban",
                                               callback_data=f'user:{"unban" if the_user.status=="banned" else "ban"}:{the_user.user_id}'))
        if kwargs.get(str(user.user_id), {}).get('can_restrict'):
            if not is_owner_or_admin(the_user):
                ls.append(InlineKeyboardButton("โ Un Restrict" if the_user.status == 'restricted' else "๐ต Restrict",
                                               callback_data=f'user:{"unrestrict" if the_user.status == "restricted" else "restrict"}:{the_user.user_id}'))

        if kwargs.get(str(user.user_id), {}).get('can_see'):
           ls.append(InlineKeyboardButton("๐ค Show Profile", callback_data=f'user:show:{the_user.user_id}'))

        if kwargs.get(str(user.user_id), {}).get('can_send'):
            if not is_owner_or_admin(the_user):
                append = True
    btn.add(*ls, row_width=2)
    if append:
        btn.add(InlineKeyboardButton("๐ Send message as admin", callback_data=f'user:send:{the_user.user_id}'))
    return btn


def on_answer_button(answer_id, message_id=0):
    btn = InlineKeyboardMarkup()
    btn.add(*[InlineKeyboardButton("๐ Edit answer", callback_data=f'edit:answer:{answer_id}:{message_id}'),
              InlineKeyboardButton('โ Post', callback_data=f'post:{answer_id}:{message_id}'),
              ])
    return btn


def setting_button():
    btn = InlineKeyboardMarkup(row_width=1)
    btn.add(
    InlineKeyboardButton("๐ Change Restriction", callback_data="setting:res"),
    InlineKeyboardButton("๐ Admins", callback_data="setting:admins")
    )
    return btn


def bot_admins_button():
    from database import Database as db
    btn = InlineKeyboardMarkup(row_width=2)
    admins = db.admins
    ls = [InlineKeyboardButton(user, callback_data=f"admin:{user}") for user in admins]
    btn.add(*ls)
    btn.add(InlineKeyboardButton("โ Add Admin", callback_data="admin:add"))
    btn.add(InlineKeyboardButton("๐ Back", callback_data="admin:back"))
    return btn
    
    
def admin_permission(user_id, **kwargs):
    btn = InlineKeyboardMarkup(row_width=2)
    btn.add(
    InlineKeyboardButton("โ Ban" if kwargs["can_ban"] else "โ Ban", callback_data=f"bot_admin:ban:{user_id}"),
    InlineKeyboardButton("โ Approve" if kwargs["can_approve"] else "โ Approve", callback_data=f"bot_admin:approve:{user_id}"),
    InlineKeyboardButton("โ Send" if kwargs["can_send"] else "โ Send", callback_data=f"bot_admin:send:{user_id}"),    InlineKeyboardButton("โ Restrict" if kwargs["can_restrict"] else "โ Restrict", callback_data=f"bot_admin:restrict:{user_id}"),
    InlineKeyboardButton("โ See profile" if kwargs["can_see"] else "โ See profile", callback_data=f"bot_admin:see:{user_id}"))
    btn.add(InlineKeyboardButton("โ Remove", callback_data=f"bot_admin:remove:{user_id}")
    )
    btn.add(InlineKeyboardButton("๐ Back", callback_data=f"bot_admin:back:{user_id}"))
    
    return btn