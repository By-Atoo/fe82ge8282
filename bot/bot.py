import os
import sqlite3
import time
from datetime import datetime
from flask import Flask, jsonify, request
import telebot
import threading

BOT_TOKEN = os.environ.get('8799985932:AAEDRskmgfdvZFpr4Oe-xiOefPvPVrvvV1o')
ADMIN_CHAT_ID = '5372601405'
API_PORT = int(os.environ.get('PORT', 8080))

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- База данных ---
def init_db():
    conn = sqlite3.connect('leaderboard.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT, score INTEGER, duration INTEGER, timestamp INTEGER)''')
    conn.commit()
    conn.close()

def save_record(name, score, duration):
    conn = sqlite3.connect('leaderboard.db')
    c = conn.cursor()
    c.execute('INSERT INTO records (name, score, duration, timestamp) VALUES (?,?,?,?)',
              (name, score, duration, int(time.time())))
    conn.commit()
    conn.close()

def get_top_records(limit=20):
    conn = sqlite3.connect('leaderboard.db')
    c = conn.cursor()
    c.execute('SELECT name, score, duration FROM records ORDER BY score DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    return [{'name': r[0], 'score': r[1], 'duration': r[2]} for r in rows]

# --- API для сайта ---
@app.route('/leaderboard', methods=['GET'])
def leaderboard():
    return jsonify(get_top_records())

@app.route('/record', methods=['POST'])
def add_record():
    data = request.get_json()
    if not data or 'name' not in data or 'score' not in data or 'duration' not in data:
        return jsonify({'success': False, 'error': 'Missing fields'}), 400
    name = data['name'][:20]
    score = int(data['score'])
    duration = int(data['duration'])
    save_record(name, score, duration)
    return jsonify({'success': True})

@app.route('/')
def index():
    return "Snake Leaderboard Bot is running"

# --- Telegram bot commands ---
@bot.message_handler(commands=['start'])
def start_msg(m):
    bot.reply_to(m, "Привет! Я бездарь!")

@bot.message_handler(commands=['top'])
def top_msg(m):
    records = get_top_records()
    if not records:
        bot.reply_to(m, "Пока нет рекордов.")
        return
    text = "🏆 ТАБЛИЦА ЛИДЕРОВ 🏆\n\n"
    for i, r in enumerate(records, 1):
        text += f"{i}. {r['name']} — {r['score']} очков ({r['duration']} сек.)\n"
    bot.reply_to(m, text)

def run_bot():
    bot.infinity_polling()

if __name__ == '__main__':
    init_db()
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=API_PORT)
