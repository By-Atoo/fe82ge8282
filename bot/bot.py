import os
import sqlite3
import time
import threading
from datetime import datetime
from flask import Flask, jsonify
import telebot

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = os.environ.get('8799985932:AAEDRskmgfdvZFpr4Oe-xiOefPvPVrvvV1o')
ADMIN_CHAT_ID = '@Atoo_o'
API_PORT = int(os.environ.get('PORT', 8080))
# -----------------

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- БАЗА ДАННЫХ (SQLite) ---
def init_db():
    conn = sqlite3.connect('leaderboard.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT,
            score INTEGER,
            duration INTEGER,
            timestamp INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def save_record(player_name, score, duration):
    conn = sqlite3.connect('leaderboard.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO records (player_name, score, duration, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (player_name, score, duration, int(time.time())))
    conn.commit()
    conn.close()

def get_top_records(limit=20):
    conn = sqlite3.connect('leaderboard.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT player_name, score, duration, timestamp
        FROM records
        ORDER BY score DESC
        LIMIT ?
    ''', (limit,))
    results = cursor.fetchall()
    conn.close()
    return results

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я занимаюсь хернёй, не трогай меня.")

@bot.message_handler(commands=['top'])
def show_top(message):
    records = get_top_records()
    if not records:
        bot.reply_to(message, "Пока нет рекордов :(")
        return
    response = "🏆 **ТАБЛИЦА ЛИДЕРОВ** 🏆\n\n"
    for idx, rec in enumerate(records, 1):
        name, score, duration, ts = rec
        date_str = datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M")
        response += f"{idx}. **{name}** — {score} очков ({duration} сек.)\n   _{date_str}_\n\n"
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_game_record(message):
    if message.text.startswith('RECORD|'):
        try:
            _, name, score_str, duration_str = message.text.split('|')
            score = int(score_str)
            duration = int(duration_str)
            top_records = get_top_records(20)
            is_top = (len(top_records) < 20 or score > top_records[-1][1])
            if is_top:
                save_record(name, score, duration)
                bot.reply_to(message, f"✅ Рекорд сохранён!\n{name} — {score} очков ({duration} сек.)\n/top — таблица")
            else:
                bot.reply_to(message, f"😔 Счёт {score} не попал в топ-20.")
        except Exception as e:
            bot.reply_to(message, f"❌ Ошибка: {str(e)}")

@app.route('/leaderboard')
def leaderboard_api():
    records = get_top_records()
    result = [{'name': name, 'score': score, 'duration': duration} for name, score, duration, _ in records]
    return jsonify(result)

@app.route('/')
def index():
    return "Bot is running!"

def run_bot():
    bot.infinity_polling()

if __name__ == '__main__':
    init_db()
    print("Бот и API запускаются...")
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    app.run(host='0.0.0.0', port=API_PORT, debug=False)
