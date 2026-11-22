
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


TEXT = {
    "en": {
        "welcome_title": "👋 Welcome, <b>{name}</b>",
        "welcome_body": (
            "Your Telegram ID: <code>{uid}</code>\n"
            "Create temporary email addresses and receive messages."
        ),
        "generate": "✉️ Generate Email",
        "inbox": "📥 My Inbox",
        "emails": "📬 My Emails",
        "profile": "👤 My Profile",
        "stats": "📊 Statistics",
        "language": "🌐 Language",
        "help": "❓ Help",
        "help_text": (
            "❓ <b>Help Center</b>\n\n"
            "/start - Start the bot\n"
            "/help - Show help\n"
            "/profile - Your profile\n"
            "/stats - Your statistics"
        ),
        "choose": "Choose an option:",
        "back": "⬅️ Back to Menu",
    },

    "bn": {
        "welcome_title": "👋 স্বাগতম, <b>{name}</b>",
        "welcome_body": (
            "আপনার Telegram ID: <code>{uid}</code>\n"
            "অস্থায়ী ইমেইল তৈরি করুন এবং ইনবক্সে মেসেজ দেখুন।"
        ),
        "generate": "✉️ নতুন ইমেইল",
        "inbox": "📥 ইনবক্স",
        "emails": "📬 আমার ইমেইল",
        "profile": "👤 প্রোফাইল",
        "stats": "📊 পরিসংখ্যান",
        "language": "🌐 ভাষা",
        "help": "❓ সাহায্য",
        "help_text": (
            "❓ <b>সাহায্য কেন্দ্র</b>\n\n"
            "/start - বট চালু করুন\n"
            "/help - সাহায্য দেখুন\n"
            "/profile - আপনার প্রোফাইল\n"
            "/stats - পরিসংখ্যান"
        ),
        "choose": "একটি অপশন নির্বাচন করুন:",
        "back": "⬅️ মূল মেনু",
    }
}


def main_menu(lang="en"):

    t = TEXT.get(lang, TEXT["en"])

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                t["generate"],
                callback_data="email:generate"
            )
        ],
        [
            InlineKeyboardButton(
                t["inbox"],
                callback_data="inbox:open"
            ),
            InlineKeyboardButton(
                t["emails"],
                callback_data="email:list"
            )
        ],
        [
            InlineKeyboardButton(
                "🗑 Delete Email",
                callback_data="email:delete:list"
            )
        ],
        [
            InlineKeyboardButton(
                t["profile"],
                callback_data="menu:profile"
            ),
            InlineKeyboardButton(
                t["stats"],
                callback_data="menu:stats"
            )
        ],
        [
            InlineKeyboardButton(
                t["language"],
                callback_data="menu:language"
            ),
            InlineKeyboardButton(
                t["help"],
                callback_data="menu:help"
            )
        ]
    ])


def language_menu():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "বাংলা",
                callback_data="lang:bn"
            ),
            InlineKeyboardButton(
                "English",
                callback_data="lang:en"
            )
        ]
    ])


def back_menu(lang="en"):

    t = TEXT.get(lang, TEXT["en"])

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                t["back"],
                callback_data="menu:home"
            )
        ]
    ])
