from aiogram.fsm.state import State, StatesGroup


class AddChat(StatesGroup):
    waiting_link = State()


class AddWord(StatesGroup):
    waiting_text = State()
    choosing_category = State()
    choosing_match_type = State()


class ImportWords(StatesGroup):
    waiting_file = State()
    confirming = State()


class SetReceiver(StatesGroup):
    waiting_forward = State()


class AddAdmin(StatesGroup):
    waiting_contact = State()
