from aiogram.fsm.state import State, StatesGroup


class RecommendationFlow(StatesGroup):
    title = State()
    author = State()
    review = State()
    photo = State()
    preview = State()
    edit_title = State()
    edit_author = State()
    edit_review = State()
    edit_photo = State()


class SupportFlow(StatesGroup):
    waiting_message = State()


class SupportReplyFlow(StatesGroup):
    waiting_message = State()


class RejectFlow(StatesGroup):
    waiting_reason = State()


class AdminEditFlow(StatesGroup):
    title = State()
    author = State()
    review = State()


class ReactionFlow(StatesGroup):
    waiting_emoji = State()


class DesignFlow(StatesGroup):
    waiting_header = State()
    waiting_footer = State()


class ChannelFlow(StatesGroup):
    waiting_target_id = State()
    waiting_target_url = State()
    waiting_sub_id = State()
    waiting_sub_url = State()


class UserSearchFlow(StatesGroup):
    waiting_query = State()


class BroadcastFlow(StatesGroup):
    waiting_text = State()
