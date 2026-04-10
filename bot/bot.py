import os
import sqlite3
import time
import json
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import threading

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = os.environ.get('TELEGRAM_TOKEN')
ADMIN_CHAT_ID = 5372601405
API_PORT = int(os.environ.get('PORT', 8080))
# -----------------

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
CORS(app)

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
    c.execute('SELECT id, name, score, duration, timestamp FROM records ORDER BY score DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'name': r[1], 'score': r[2], 'duration': r[3], 'timestamp': r[4]} for r in rows]

def get_all_records(order_by='score DESC'):
    conn = sqlite3.connect('leaderboard.db')
    c = conn.cursor()
    c.execute(f'SELECT id, name, score, duration, timestamp FROM records ORDER BY {order_by}')
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'name': r[1], 'score': r[2], 'duration': r[3], 'timestamp': r[4]} for r in rows]

def delete_record(record_id):
    conn = sqlite3.connect('leaderboard.db')
    c = conn.cursor()
    c.execute('DELETE FROM records WHERE id = ?', (record_id,))
    conn.commit()
    conn.close()

def delete_all_records():
    conn = sqlite3.connect('leaderboard.db')
    c = conn.cursor()
    c.execute('DELETE FROM records')
    conn.commit()
    conn.close()

def update_record(record_id, field, value):
    conn = sqlite3.connect('leaderboard.db')
    c = conn.cursor()
    c.execute(f'UPDATE records SET {field} = ? WHERE id = ?', (value, record_id))
    conn.commit()
    conn.close()

def get_record_by_id(record_id):
    conn = sqlite3.connect('leaderboard.db')
    c = conn.cursor()
    c.execute('SELECT id, name, score, duration, timestamp FROM records WHERE id = ?', (record_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'id': row[0], 'name': row[1], 'score': row[2], 'duration': row[3], 'timestamp': row[4]}
    return None

def search_records_by_name(query):
    conn = sqlite3.connect('leaderboard.db')
    c = conn.cursor()
    c.execute('SELECT id, name, score, duration, timestamp FROM records WHERE name LIKE ? ORDER BY score DESC', (f'%{query}%',))
    rows = c.fetchall()
    conn.close()
    return [{'id': r[0], 'name': r[1], 'score': r[2], 'duration': r[3], 'timestamp': r[4]} for r in rows]

def get_statistics():
    conn = sqlite3.connect('leaderboard.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*), AVG(score), MAX(score), MIN(score) FROM records')
    count, avg, max_score, min_score = c.fetchone()
    conn.close()
    return {
        'count': count or 0,
        'avg': round(avg, 2) if avg else 0,
        'max': max_score or 0,
        'min': min_score or 0
    }

@app.route('/leaderboard', methods=['GET', 'OPTIONS'])
def leaderboard():
    if request.method == 'OPTIONS':
        return '', 200
    records = get_top_records(20)
    return jsonify([{'name': r['name'], 'score': r['score'], 'duration': r['duration']} for r in records])

@app.route('/record', methods=['POST', 'OPTIONS'])
def add_record():
    if request.method == 'OPTIONS':
        return '', 200
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
    return "Snake Leaderboard Bot with Admin Panel"

@bot.message_handler(commands=['start'])
def start_msg(m):
    bot.reply_to(m, "Привет, Я бездарь!")

@bot.message_handler(commands=['top'])
def top_msg(m):
    records = get_top_records(20)
    if not records:
        bot.reply_to(m, "Пока нет рекордов.")
        return
    text = "🏆ТАБЛИЦА ЛИДЕРОВ🏆\n\n"
    for i, r in enumerate(records, 1):
        text += f"{i}. {r['name']} — {r['score']} очков ({r['duration']} сек.)\n"
    bot.reply_to(m, text)

def is_admin(chat_id):
    return chat_id == ADMIN_CHAT_ID

@bot.message_handler(commands=['admin'])
def admin_panel(m):
    if not is_admin(m.chat.id):
        bot.reply_to(m, "⛔ У вас нет доступа к этой команде.")
        return
    show_admin_menu(m.chat.id)

def show_admin_menu(chat_id):
    markup = InlineKeyboardMarkup(row_width=2)
    btn1 = InlineKeyboardButton("📋 Все рекорды", callback_data="admin_list")
    btn2 = InlineKeyboardButton("🔍 Поиск по имени", callback_data="admin_search")
    btn3 = InlineKeyboardButton("➕ Добавить тестовый рекорд", callback_data="admin_add_test")
    btn4 = InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")
    btn5 = InlineKeyboardButton("🗑️ Удалить все рекорды", callback_data="admin_delete_all_confirm")
    btn6 = InlineKeyboardButton("💾 Экспорт (JSON)", callback_data="admin_export_json")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    bot.send_message(chat_id, "🔐 **Админ-панель**\nВыберите действие:", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def handle_admin_callbacks(call):
    if not is_admin(call.message.chat.id):
        bot.answer_callback_query(call.id, "⛔ Нет прав")
        return
    data = call.data
    if data == 'admin_list':
        show_records_list(call.message.chat.id, page=0)
    elif data == 'admin_search':
        bot.send_message(call.message.chat.id, "Введите имя (или часть имени) для поиска:")
        bot.register_next_step_handler(call.message, process_search_query)
    elif data == 'admin_add_test':
        add_test_record(call.message.chat.id)
    elif data == 'admin_stats':
        show_stats(call.message.chat.id)
    elif data == 'admin_delete_all_confirm':
        confirm_delete_all(call.message.chat.id)
    elif data == 'admin_export_json':
        export_json(call.message.chat.id)
    elif data.startswith('admin_page_'):
        page = int(data.split('_')[-1])
        show_records_list(call.message.chat.id, page)
    elif data.startswith('admin_edit_'):
        record_id = int(data.split('_')[-1])
        show_edit_menu(call.message.chat.id, record_id)
    elif data.startswith('admin_edit_field_'):
        parts = data.split('_')
        record_id = int(parts[3])
        field = parts[4]  # name, score, duration
        ask_for_new_value(call.message.chat.id, record_id, field)
    elif data.startswith('admin_delete_one_'):
        record_id = int(data.split('_')[-1])
        delete_one_record(call.message.chat.id, record_id)
    elif data == 'admin_delete_all_yes':
        delete_all_records()
        bot.send_message(call.message.chat.id, "✅ Все рекорды удалены.")
        show_admin_menu(call.message.chat.id)
    elif data == 'admin_delete_all_no':
        bot.send_message(call.message.chat.id, "Операция отменена.")
        show_admin_menu(call.message.chat.id)
    bot.answer_callback_query(call.id)

def show_records_list(chat_id, page=0, records=None, per_page=5):
    if records is None:
        records = get_all_records()
    total = len(records)
    start = page * per_page
    end = start + per_page
    page_records = records[start:end]
    if not page_records:
        bot.send_message(chat_id, "Нет записей.")
        return
    text = f"📋 **Рекорды (стр. {page+1} из { (total+per_page-1)//per_page if total else 1 })**\n\n"
    for r in page_records:
        date_str = datetime.fromtimestamp(r['timestamp']).strftime("%d.%m.%y %H:%M")
        text += f"`ID: {r['id']}`\n👤 {r['name']} | 🍎 {r['score']} | ⏱️ {r['duration']} сек.\n_{date_str}_\n\n"
    markup = InlineKeyboardMarkup()
    if page > 0:
        markup.add(InlineKeyboardButton("◀ Назад", callback_data=f"admin_page_{page-1}"))
    if end < total:
        markup.add(InlineKeyboardButton("Вперед ▶", callback_data=f"admin_page_{page+1}"))
    for r in page_records:
        markup.add(InlineKeyboardButton(f"✏️ Редактировать ID {r['id']} ({r['name']})", callback_data=f"admin_edit_{r['id']}"))
    markup.add(InlineKeyboardButton("🔙 В меню", callback_data="admin_back_to_menu"))
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode='Markdown')

def show_edit_menu(chat_id, record_id):
    rec = get_record_by_id(record_id)
    if not rec:
        bot.send_message(chat_id, "Запись не найдена.")
        return
    text = f"✏️ **Редактирование ID {rec['id']}**\n\n👤 Имя: `{rec['name']}`\n🍎 Очки: `{rec['score']}`\n⏱️ Время: `{rec['duration']}` сек.\n\nЧто хотите изменить?"
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📝 Имя", callback_data=f"admin_edit_field_{record_id}_name"))
    markup.add(InlineKeyboardButton("🔢 Очки", callback_data=f"admin_edit_field_{record_id}_score"))
    markup.add(InlineKeyboardButton("⏱️ Время", callback_data=f"admin_edit_field_{record_id}_duration"))
    markup.add(InlineKeyboardButton("🗑️ Удалить запись", callback_data=f"admin_delete_one_{record_id}"))
    markup.add(InlineKeyboardButton("🔙 Назад к списку", callback_data="admin_list"))
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode='Markdown')

def ask_for_new_value(chat_id, record_id, field):
    field_names = {'name': 'имя', 'score': 'очки', 'duration': 'время (сек)'}
    bot.send_message(chat_id, f"Введите новое значение для поля **{field_names[field]}** (ID {record_id}):", parse_mode='Markdown')
    bot.register_next_step_handler_by_chat_id(chat_id, lambda msg: update_record_field(msg, record_id, field))

def update_record_field(message, record_id, field):
    if not is_admin(message.chat.id):
        return
    new_value = message.text.strip()
    if field == 'score' or field == 'duration':
        try:
            new_value = int(new_value)
        except:
            bot.send_message(message.chat.id, "❌ Ошибка: введите целое число.")
            return
    update_record(record_id, field, new_value)
    bot.send_message(message.chat.id, f"✅ Поле `{field}` обновлено на `{new_value}`.", parse_mode='Markdown')
    show_edit_menu(message.chat.id, record_id)

def delete_one_record(chat_id, record_id):
    rec = get_record_by_id(record_id)
    if rec:
        delete_record(record_id)
        bot.send_message(chat_id, f"✅ Рекорд ID {record_id} удалён.")
    else:
        bot.send_message(chat_id, "Запись не найдена.")
    show_records_list(chat_id, page=0)

def confirm_delete_all(chat_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ ДА, УДАЛИТЬ ВСЁ", callback_data="admin_delete_all_yes"))
    markup.add(InlineKeyboardButton("❌ НЕТ, ОТМЕНА", callback_data="admin_delete_all_no"))
    bot.send_message(chat_id, "⚠️ **Вы уверены, что хотите удалить ВСЕ рекорды?** Это действие необратимо.", reply_markup=markup, parse_mode='Markdown')

def add_test_record(chat_id):
    import random
    test_names = ["Тестер", "Чемпион", "Новичок", "Стример", "Гость"]
    name = random.choice(test_names) + str(random.randint(1, 99))
    score = random.randint(50, 500)
    duration = random.randint(20, 120)
    save_record(name, score, duration)
    bot.send_message(chat_id, f"✅ Добавлен тестовый рекорд: {name} — {score} очков ({duration} сек.)")
    show_admin_menu(chat_id)

def show_stats(chat_id):
    stats = get_statistics()
    text = f"📊 **Статистика**\n\n"
    text += f"Всего рекордов: {stats['count']}\n"
    text += f"Средний счёт: {stats['avg']}\n"
    text += f"Максимальный счёт: {stats['max']}\n"
    text += f"Минимальный счёт: {stats['min']}\n"
    bot.send_message(chat_id, text, parse_mode='Markdown')

def export_json(chat_id):
    records = get_all_records()
    data = []
    for r in records:
        data.append({
            'id': r['id'],
            'name': r['name'],
            'score': r['score'],
            'duration': r['duration'],
            'timestamp': r['timestamp'],
            'date': datetime.fromtimestamp(r['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
        })
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    import io
    file = io.BytesIO(json_str.encode('utf-8'))
    file.name = "leaderboard_export.json"
    bot.send_document(chat_id, file, caption="📁 Экспорт всех рекордов в JSON")

def process_search_query(message):
    if not is_admin(message.chat.id):
        return
    query = message.text.strip()
    if len(query) < 2:
        bot.send_message(message.chat.id, "Введите минимум 2 символа для поиска.")
        return
    records = search_records_by_name(query)
    if not records:
        bot.send_message(message.chat.id, f"Ничего не найдено по запросу `{query}`.", parse_mode='Markdown')
        return
    show_records_list(message.chat.id, page=0, records=records)

@bot.callback_query_handler(func=lambda call: call.data == 'admin_back_to_menu')
def back_to_menu(call):
    if not is_admin(call.message.chat.id):
        bot.answer_callback_query(call.id, "⛔ Нет прав")
        return
    show_admin_menu(call.message.chat.id)
    bot.answer_callback_query(call.id)

def run_bot():
    bot.infinity_polling()

if __name__ == '__main__':
    init_db()
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=API_PORT)
