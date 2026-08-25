"""FSM holatlar — foydalanuvchi va admin oqimlari."""
from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    stars_custom = State()      # kustom miqdor
    stars_username = State()    # Stars: username kiritish
    premium_username = State()  # Premium: username
    nft_target = State()        # NFT: havola/username
    gift_username = State()     # Gift: username
    reaction_link = State()     # Post link
    topup_amount = State()      # Balans: summa
    topup_last4 = State()       # Balans: oxirgi 4 raqam
    support_text = State()      # Murojaat


class AdminStates(StatesGroup):
    user_search = State()
    balance_add = State()
    balance_sub = State()
    card_number = State()
    card_name = State()
    setting_value = State()     # generic (data['key'] da)
    broadcast_msg = State()
    acc_phone = State()         # telefon
    acc_code = State()          # login kod
    acc_2fa = State()           # 2FA parol
    acc_name = State()          # hisob nomi
    stock_phone = State()
    stock_twofa = State()
    stock_price = State()
    stock_country = State()
    stock_note = State()
    stock_file = State()        # server2 sessiya fayli yuklash
    nft_result = State()        # NFT natijasi
    ticket_reply = State()      # javob xat
    country_price = State()
