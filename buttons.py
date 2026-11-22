from telegram import InlineKeyboardButton, InlineKeyboardMarkup

TEXT = {
 "en": {
  "welcome": "Welcome to *Temp Mail Bot*\\nCreate temporary inboxes and view incoming messages.",
  "generate": "✉️ Generate email", "inbox": "📥 My inbox", "emails": "📬 My emails",
  "profile": "👤 My profile", "stats": "📊 Statistics", "language": "🌐 Language",
  "help": "❓ Help", "choose": "Choose an option:"
 },
 "bn": {
  "welcome": "Temp Mail Bot-এ স্বাগতম।\\nঅস্থায়ী ইমেইল তৈরি করুন এবং আসা মেসেজ দেখুন।",
  "generate": "✉️ নতুন ইমেইল", "inbox": "📥 ইনবক্স", "emails": "📬 আমার ইমেইল",
  "profile": "👤 প্রোফাইল", "stats": "📊 পরিসংখ্যান", "language": "🌐 ভাষা",
  "help": "❓ সাহায্য", "choose": "একটি অপশন নির্বাচন করুন:"
 }
}

def main_menu(lang="en"):
    t = TEXT.get(lang, TEXT["en"])
    return InlineKeyboardMarkup([
      [InlineKeyboardButton(t["generate"], callback_data="email:generate")],
      [InlineKeyboardButton(t["inbox"], callback_data="inbox:open"),
       InlineKeyboardButton(t["emails"], callback_data="email:list")],
      [InlineKeyboardButton("🗑 Delete email", callback_data="email:delete:list")],
      [InlineKeyboardButton(t["profile"], callback_data="menu:profile"),
       InlineKeyboardButton(t["stats"], callback_data="menu:stats")],
      [InlineKeyboardButton(t["language"], callback_data="menu:language"),
       InlineKeyboardButton(t["help"], callback_data="menu:help")]
    ])

def language_menu():
    return InlineKeyboardMarkup([
      [InlineKeyboardButton("বাংলা", callback_data="lang:bn"),
       InlineKeyboardButton("English", callback_data="lang:en")]
    ])

def back_menu(lang="en"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menu", callback_data="menu:home")]])
