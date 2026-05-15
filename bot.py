import os
import random
import string
import threading
import requests
from flask import Flask, render_template, request, jsonify
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Configuración de variables desde el panel de Render
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
APPS_SCRIPT_URL = os.getenv('APPS_SCRIPT_URL')
URL_BASE = os.getenv('URL_BASE')

app = Flask(__name__)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ==========================================
# RUTAS DE LA PÁGINA WEB (FLASK)
# ==========================================
@app.route('/')
def index():
    # Inyectamos la URL de la base de datos directamente al HTML
    return render_template('index.html', link_base_datos=APPS_SCRIPT_URL)

@app.route('/api/crear', methods=['POST'])
def api_crear():
    data = request.json
    horas = data.get('horas', 24)
    sala_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    
    try:
        payload = {'action': 'create_room', 'sala': sala_id, 'horas': horas}
        requests.post(APPS_SCRIPT_URL, data=payload)
        enlace_final = f"{URL_BASE}/?sala={sala_id}"
        return jsonify({"exito": True, "link": enlace_final, "sala": sala_id})
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500

# ==========================================
# LÓGICA DEL BOT DE TELEGRAM (INTERACTIVO)
# ==========================================
@bot.message_handler(commands=['start', 'menu'])
def menu_principal(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🏢 Crear Nueva Sala", callback_data="accion_crear"))
    bot.send_message(message.chat.id, "Bienvenido a *NimbusBoard Workspace*.\nSeleccione una acción:", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "accion_crear")
def seleccionar_tiempo(call):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("12 Horas", callback_data="tiempo_12"), InlineKeyboardButton("24 Horas", callback_data="tiempo_24"))
    markup.row(InlineKeyboardButton("48 Horas", callback_data="tiempo_48"), InlineKeyboardButton("72 Horas", callback_data="tiempo_72"))
    markup.add(InlineKeyboardButton("❌ Cancelar", callback_data="volver_inicio"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="⏳ Seleccione el tiempo de caducidad:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("tiempo_"))
def generar_enlace(call):
    horas = call.data.split("_")[1]
    sala_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="⚙️ Registrando entorno...")
    
    try:
        requests.post(APPS_SCRIPT_URL, data={'action': 'create_room', 'sala': sala_id, 'horas': horas})
        enlace_final = f"{URL_BASE}/?sala={sala_id}"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 Volver al Menú", callback_data="volver_inicio"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                              text=f"✅ *Entorno Generado*\n\n🔑 ID: `{sala_id}`\n⏳ Caducidad: {horas} horas\n🔗 Acceso: {enlace_final}", 
                              parse_mode="Markdown", reply_markup=markup)
    except:
        bot.send_message(call.message.chat.id, "⚠️ Error de base de datos.")

@bot.callback_query_handler(func=lambda call: call.data == "volver_inicio")
def volver_inicio(call):
    menu_principal(call.message)

def iniciar_bot():
    bot.infinity_polling()

if __name__ == '__main__':
    threading.Thread(target=iniciar_bot, daemon=True).start()
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=puerto)
