#  ▒▒▒▒██  ██     ----------------------------------------
#      ██         | АВТОР - divargia                     |
#  ██████▒▒██     | ГитХаб - https://github.com/Divargia |
#  ██  ██  ██     | Телеграм - @divargia                 |
#  ██████  ██     ----------------------------------------
#
#  Подарок от диви (добри анон) для администрации ннкф.

import logging
from telegram.ext import JobQueue
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import json
import os
import time
from datetime import datetime
import asyncio
import sys

###Настройка базового логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

###Файлы для хранения данных
DATA_FILE = "messages_data.json"
CONFIG_FILE = "bot_config.json"
USERS_FILE = "bot_users.json"
LOG_FILE = "bot_daily_log.txt"
MUTE_QUEUE_FILE = "mute_queue.json"
BANNED_USERS_FILE = "banned_users.json"
REBOOT_STATE_FILE = "reboot_state.json"

class BotLogger:
    """Класс для ведения отдельного лог файла с важными событиями"""
    
    @staticmethod
    def log(message):
        """Записывает важные события в лог файл"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            print(f"📝 LOG: {message}")
        except Exception as e:
            logger.error(f"Ошибка записи в лог: {e}")
    
    @staticmethod
    def get_today_logs():
        """Получает логи за сегодняшний день"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if not os.path.exists(LOG_FILE):
            return "📭 Логов за сегодня нет."
        
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                all_logs = f.readlines()
            
            today_logs = [log for log in all_logs if log.startswith(f"[{today}")]
            
            if not today_logs:
                return "📭 Логов за сегодня нет."
            
            return "".join(today_logs)
        except Exception as e:
            return f"❌ Ошибка чтения логов: {e}"

class BannedUsers:
    """Класс для управления забаненными пользователями"""
    
    def __init__(self):
        self.banned = self.load_banned()
    
    def load_banned(self):
        if os.path.exists(BANNED_USERS_FILE):
            try:
                with open(BANNED_USERS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_banned(self):
        with open(BANNED_USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.banned, f, ensure_ascii=False, indent=2)
    
    def ban_user(self, user_id, username=None, reason=""):
        """Банит пользователя"""
        user_key = str(user_id)
        self.banned[user_key] = {
            'user_id': user_id,
            'username': username,
            'banned_at': int(time.time()),
            'reason': reason
        }
        self.save_banned()
        BotLogger.log(f"🚫 Пользователь {user_id} (@{username}) забанен: {reason}")
    
    def unban_user(self, user_id):
        """Разбанивает пользователя"""
        user_key = str(user_id)
        if user_key in self.banned:
            username = self.banned[user_key].get('username')
            del self.banned[user_key]
            self.save_banned()
            BotLogger.log(f"✅ Пользователь {user_id} (@{username}) разбанен")
            return True
        return False
    
    def is_banned(self, user_id):
        """Проверяет, забанен ли пользователь"""
        return str(user_id) in self.banned
    
    def get_all_banned(self):
        """Возвращает список всех забаненных"""
        return list(self.banned.values())

class RebootState:
    """Класс для управления состоянием перезагрузки"""
    
    @staticmethod
    def save_reboot_info(chat_id, message_id, admin_id):
        """Сохраняет информацию о перезагрузке"""
        reboot_info = {
            'chat_id': chat_id,
            'message_id': message_id,
            'admin_id': admin_id,
            'timestamp': int(time.time())
        }
        with open(REBOOT_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(reboot_info, f)
    
    @staticmethod
    def get_and_clear_reboot_info():
        """Получает и очищает информацию о перезагрузке"""
        if not os.path.exists(REBOOT_STATE_FILE):
            return None
        
        try:
            with open(REBOOT_STATE_FILE, 'r', encoding='utf-8') as f:
                reboot_info = json.load(f)
            
            # Удаляем файл после прочтения
            os.remove(REBOOT_STATE_FILE)
            return reboot_info
        except:
            return None

class MuteQueue:
    """Класс для управления очередью сообщений во время заглушки"""
    
    def __init__(self):
        self.queue = self.load_queue()
    
    def load_queue(self):
        if os.path.exists(MUTE_QUEUE_FILE):
            try:
                with open(MUTE_QUEUE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_queue(self):
        with open(MUTE_QUEUE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.queue, f, ensure_ascii=False, indent=2)
    
    def add_message(self, user_id, message_data, timestamp):
        """Добавляет сообщение в очередь"""
        self.queue.append({
            'user_id': user_id,
            'message_data': message_data,
            'timestamp': timestamp
        })
        self.save_queue()
        BotLogger.log(f"📥 Сообщение от {user_id} добавлено в очередь (режим заглушки)")
    
    def get_and_clear_queue(self):
        """Получает все сообщения из очереди и очищает её"""
        queue_copy = self.queue.copy()
        self.queue = []
        self.save_queue()
        return queue_copy

class BotConfig:
    def __init__(self):
        self.config = self.load_config()
    
    def load_config(self):
        """Загружает конфигурацию из файла"""
        default_config = {
            # === ОСНОВНЫЕ НАСТРОЙКИ ===
            "токен-бота": "8384608414:AAFJdRpQvMosCUiFgmdusk3Bk3TwTAPGWZY",
            "айди-группы": "-1002815027615",
            "айди-канала": "-1002879231816",
            
            # === ФУНКЦИИ БОТА ===
            "принимать-сообщения": True,          # Принимать сообщения от пользователей
            "принимать-медиа": True,              # Принимать фото/видео/файлы
            "рассылки-включены": True,            # Разрешить рассылки
            "заглушка-включена": False,           # Режим заглушки (новый параметр)
            
            # === АНОНИМНОСТЬ ===
            "анонимные-авторы": False,            # Скрывать авторов сообщений
            "анонимные-ответы": True,             # Скрывать тех, кто отвечает
            
            # === АДМИНИСТРАТОРЫ ===
            "админы": []                          # ID админов для настроек
        }
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Обновляем только существующие ключи
                    for key, value in loaded_config.items():
                        if key in default_config:
                            default_config[key] = value
                    return default_config
            except:
                pass
        
        # Сохраняем конфиг по умолчанию
        self.save_config(default_config)
        return default_config
    
    def save_config(self, config=None):
        """Сохраняет конфигурацию в файл"""
        if config is None:
            config = self.config
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def get(self, key):
        """Получает значение настройки"""
        return self.config.get(key)
    
    def set(self, key, value):
        """Устанавливает значение настройки"""
        old_value = self.config.get(key)
        self.config[key] = value
        self.save_config()
        BotLogger.log(f"⚙️ Настройка '{key}' изменена: {old_value} → {value}")

class UserStorage:
    def __init__(self):
        self.users = self.load_users()
    
    def load_users(self):
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_users(self):
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, ensure_ascii=False, indent=2)
    
    def add_user(self, user_id, username=None, first_name=None):
        """Добавляет пользователя в базу"""
        user_key = str(user_id)
        is_new_user = user_key not in self.users
        
        self.users[user_key] = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'last_activity': str(int(time.time()))
        }
        self.save_users()
        
        if is_new_user:
            BotLogger.log(f"👤 Новый пользователь: {user_id} (@{username}) - всего пользователей: {len(self.users)}")
        
        print(f"✅ Пользователь {user_id} (@{username}) {'добавлен' if is_new_user else 'обновлён'} в базе")
        print(f"🔍 Всего пользователей в базе: {len(self.users)}")
    
    def get_all_users(self):
        """Возвращает список всех пользователей"""
        users_list = list(self.users.values())
        print(f"🔍 Запрос всех пользователей: найдено {len(users_list)}")
        for user in users_list:
            print(f"   - {user['user_id']} (@{user.get('username', 'нет')})")
        return users_list

class MessageStorage:
    def __init__(self):
        self.data = self.load_data()
    
    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_data(self):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def store_message(self, group_message_id, user_id, message_data, username=None):
        """Сохраняет данные сообщения"""
        key = str(group_message_id)
        self.data[key] = {
            'user_id': user_id,
            'username': username,
            'message_data': message_data
        }
        self.save_data()
    
    def get_message_data(self, group_message_id):
        return self.data.get(str(group_message_id))
    
    def remove_message(self, group_message_id):
        key = str(group_message_id)
        if key in self.data:
            del self.data[key]
            self.save_data()

# Глобальные объекты
config = BotConfig()
storage = MessageStorage()
user_storage = UserStorage()
mute_queue = MuteQueue()
bot_logger = BotLogger()
banned_users = BannedUsers()

# Состояние для рассылки и перезагрузки
mailing_state = {}
reboot_confirmation = {}

def is_admin(user_id):
    """Проверяет, является ли пользователь админом"""
    return user_id in config.get('админы')

def get_message_info(message):
    """Извлекает информацию о сообщении"""
    message_data = {
        'type': 'text',
        'content': None,
        'caption': None
    }
    
    if message.text:
        message_data['type'] = 'text'
        message_data['content'] = message.text
    elif message.photo:
        message_data['type'] = 'photo'
        message_data['content'] = message.photo[-1].file_id
        message_data['caption'] = message.caption or ""
    elif message.video:
        message_data['type'] = 'video'
        message_data['content'] = message.video.file_id
        message_data['caption'] = message.caption or ""
    elif message.document:
        if message.document.mime_type and message.document.mime_type.startswith(('image/', 'video/')):
            message_data['type'] = 'document'
            message_data['content'] = message.document.file_id
            message_data['caption'] = message.caption or ""
        else:
            return None
    else:
        return None
    
    return message_data

def get_message_info_extended(message):
    """Расширенная версия извлечения информации о сообщении для рассылки"""
    message_data = {
        'type': 'text',
        'content': None,
        'caption': None
    }
    
    if message.text:
        message_data['type'] = 'text'
        message_data['content'] = message.text
    elif message.photo:
        message_data['type'] = 'photo'
        message_data['content'] = message.photo[-1].file_id
        message_data['caption'] = message.caption or ""
    elif message.video:
        message_data['type'] = 'video'
        message_data['content'] = message.video.file_id
        message_data['caption'] = message.caption or ""
    elif message.document:
        message_data['type'] = 'document'
        message_data['content'] = message.document.file_id
        message_data['caption'] = message.caption or ""
    elif message.animation:
        message_data['type'] = 'animation'
        message_data['content'] = message.animation.file_id
        message_data['caption'] = message.caption or ""
    elif message.voice:
        message_data['type'] = 'voice'
        message_data['content'] = message.voice.file_id
        message_data['caption'] = message.caption or ""
    elif message.audio:
        message_data['type'] = 'audio'
        message_data['content'] = message.audio.file_id
        message_data['caption'] = message.caption or ""
    else:
        return None
    
    return message_data

async def send_mailing_message(context, chat_id, message_data, mailing_text):
    """Отправляет сообщение рассылки"""
    try:
        if message_data['type'] == 'text':
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📢 РАССЫЛКА:\n\n{mailing_text}"
            )
        elif message_data['type'] == 'photo':
            caption = f"📢 РАССЫЛКА:\n\n{mailing_text}"
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=message_data['content'],
                caption=caption
            )
        elif message_data['type'] == 'video':
            caption = f"📢 РАССЫЛКА:\n\n{mailing_text}"
            await context.bot.send_video(
                chat_id=chat_id,
                video=message_data['content'],
                caption=caption
            )
        elif message_data['type'] == 'document':
            caption = f"📢 РАССЫЛКА:\n\n{mailing_text}"
            await context.bot.send_document(
                chat_id=chat_id,
                document=message_data['content'],
                caption=caption
            )
        elif message_data['type'] == 'animation':
            caption = f"📢 РАССЫЛКА:\n\n{mailing_text}"
            await context.bot.send_animation(
                chat_id=chat_id,
                animation=message_data['content'],
                caption=caption
            )
        elif message_data['type'] == 'voice':
            await context.bot.send_voice(
                chat_id=chat_id,
                voice=message_data['content']
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📢 РАССЫЛКА:\n\n{mailing_text}"
            )
        elif message_data['type'] == 'audio':
            caption = f"📢 РАССЫЛКА:\n\n{mailing_text}"
            await context.bot.send_audio(
                chat_id=chat_id,
                audio=message_data['content'],
                caption=caption
            )
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки рассылки пользователю {chat_id}: {e}")
        return False

async def send_message_to_group(context, message_data, author_info, reply_markup):
    """Отправляет сообщение в группу"""
    group_id = config.get('айди-группы')
    
    if config.get('анонимные-авторы'):
        author_text = "📩 Анонимное сообщение"
    else:
        author_text = f"📩 Сообщение от {author_info}"
    
    if message_data['type'] == 'text':
        forward_text = f"{author_text}:\n\n{message_data['content']}"
        return await context.bot.send_message(
            chat_id=group_id,
            text=forward_text,
            reply_markup=reply_markup
        )
    elif message_data['type'] == 'photo':
        caption = author_text
        if message_data['caption']:
            caption += f":\n\n{message_data['caption']}"
        return await context.bot.send_photo(
            chat_id=group_id,
            photo=message_data['content'],
            caption=caption,
            reply_markup=reply_markup
        )
    elif message_data['type'] == 'video':
        caption = author_text
        if message_data['caption']:
            caption += f":\n\n{message_data['caption']}"
        return await context.bot.send_video(
            chat_id=group_id,
            video=message_data['content'],
            caption=caption,
            reply_markup=reply_markup
        )
    elif message_data['type'] == 'document':
        caption = author_text
        if message_data['caption']:
            caption += f":\n\n{message_data['caption']}"
        return await context.bot.send_document(
            chat_id=group_id,
            document=message_data['content'],
            caption=caption,
            reply_markup=reply_markup
        )

async def send_message_to_channel(context, message_data):
    """Отправляет сообщение в канал"""
    channel_id = config.get('айди-канала')
    
    if message_data['type'] == 'text':
        return await context.bot.send_message(
            chat_id=channel_id,
            text=message_data['content']
        )
    elif message_data['type'] == 'photo':
        return await context.bot.send_photo(
            chat_id=channel_id,
            photo=message_data['content'],
            caption=message_data['caption']
        )
    elif message_data['type'] == 'video':
        return await context.bot.send_video(
            chat_id=channel_id,
            video=message_data['content'],
            caption=message_data['caption']
        )
    elif message_data['type'] == 'document':
        return await context.bot.send_document(
            chat_id=channel_id,
            document=message_data['content'],
            caption=message_data['caption']
        )

async def process_queued_messages(context):
    """Обрабатывает сообщения из очереди после отключения заглушки"""
    queued_messages = mute_queue.get_and_clear_queue()
    
    if not queued_messages:
        return
    
    BotLogger.log(f"📤 Обработка {len(queued_messages)} сообщений из очереди")
    
    for queued_msg in queued_messages:
        try:
            user_id = queued_msg['user_id']
            message_data = queued_msg['message_data']
            
            keyboard = [[InlineKeyboardButton("📤 Опубликовать в канал", callback_data="publish")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Формируем информацию об авторе
            user_info = user_storage.users.get(str(user_id), {})
            username = user_info.get('username')
            first_name = user_info.get('first_name')
            author_info = f"@{username}" if username else first_name or "пользователя"
            
            sent_message = await send_message_to_group(context, message_data, author_info, reply_markup)
            
            storage.store_message(
                group_message_id=sent_message.message_id,
                user_id=user_id,
                message_data=message_data,
                username=username or first_name
            )
            
            # Уведомляем пользователя
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ Ваше сообщение (отправленное во время заглушки) было доставлено в группу!"
            )
            
            BotLogger.log(f"✅ Сообщение от {user_id} из очереди обработано и отправлено в группу")
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения из очереди: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    
    # Сохраняем пользователя при /start
    user_storage.add_user(user.id, user.username, user.first_name)
    
    if not config.get('принимать-сообщения'):
        await update.message.reply_text("🚫 Бот временно не принимает сообщения.")
        return
    
    help_text = "🤖 Привет! Вот что я умею:\n\n"
    help_text += "📝 Отправь мне текст - я перешлю его в группу\n"
    
    if config.get('принимать-медиа'):
        help_text += "📸 Отправь фото/видео - я тоже их перешлю\n"
    
    help_text += "\n💡 В группе твоё сообщение можно будет опубликовать в канал"
    
    if config.get('анонимные-авторы'):
        help_text += "\n🕶 Твоя личность будет скрыта"
    
    await update.message.reply_text(help_text)

async def handle_mailing_or_regular_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ВСЕХ сообщений в приватном чате"""
    user = update.effective_user
    message = update.message
    
    # Проверяем, не забанен ли пользователь
    if banned_users.is_banned(user.id):
        await message.reply_text("🚫 Вы заблокированы в этом боте.")
        BotLogger.log(f"🚫 Заблокированный пользователь {user.id} попытался отправить сообщение")
        return
    
    # Сохраняем пользователя в базу
    user_storage.add_user(user.id, user.username, user.first_name)
    
    print(f"🔍 ОБРАБОТЧИК: сообщение от {user.id}: '{message.text if message.text else 'медиа'}'")
    print(f"🔍 Состояние рассылки: {mailing_state}")
    print(f"🔍 Пользователь админ: {is_admin(user.id)}")
    
    # РАССЫЛКА ДЛЯ АДМИНОВ (поддержка медиа)
    if user.id in mailing_state and mailing_state[user.id]:
        print(f"📢 >>> ЗАПУСКАЕМ РАССЫЛКУ ОТ АДМИНА <<<")
        mailing_state[user.id] = False  # Сбрасываем состояние
        
        # Получаем данные сообщения
        message_data = get_message_info_extended(message)
        
        if not message_data:
            await message.reply_text("❌ Неподдерживаемый тип сообщения для рассылки.")
            return
        
        # Получаем всех пользователей
        all_users = user_storage.get_all_users()
        
        if not all_users:
            await message.reply_text("❌ Нет пользователей для рассылки.")
            return
        
        # Отправляем рассылку
        success_count = 0
        error_count = 0
        
        status_message = await message.reply_text(f"📤 Отправляю рассылку {len(all_users)} пользователям...")
        
        BotLogger.log(f"📢 Админ {user.id} запустил рассылку для {len(all_users)} пользователей")
        
        # Текст для рассылки
        mailing_text = message.text or message.caption or "Медиа-файл"
        
        for user_data in all_users:
            # Не отправляем админу самому себе и забаненным
            if user_data['user_id'] != user.id and not banned_users.is_banned(user_data['user_id']):
                success = await send_mailing_message(
                    context, 
                    user_data['user_id'], 
                    message_data, 
                    mailing_text
                )
                if success:
                    success_count += 1
                    print(f"✅ Рассылка отправлена пользователю {user_data['user_id']}")
                else:
                    error_count += 1
        
        # Отчет о рассылке
        BotLogger.log(f"📊 Рассылка завершена: успешно {success_count}, ошибок {error_count}")
        
        await status_message.edit_text(
            f"✅ Рассылка завершена!\n\n"
            f"📤 Успешно: {success_count}\n"
            f"❌ Ошибок: {error_count}\n"
            f"👥 Всего пользователей: {len(all_users)}"
        )
        return
    
    # ОБЫЧНЫЕ СООБЩЕНИЯ
    if message.chat.type != 'private':
        return
    
    # Проверяем, включен ли приём сообщений
    if not config.get('принимать-сообщения'):
        await message.reply_text("🚫 Бот временно не принимает сообщения.")
        return
    
    # ПРОВЕРКА РЕЖИМА ЗАГЛУШКИ
    if config.get('заглушка-включена'):
        try:
            message_info = get_message_info(message)
            if message_info:
                mute_queue.add_message(user.id, message_info, int(time.time()))
                await message.reply_text("🔇 Сообщения временно заглушены. Ваше сообщение сохранено и будет отправлено после включения бота.")
                return
        except Exception as e:
            logger.error(f"Ошибка сохранения в очередь: {e}")
            await message.reply_text("❌ Ошибка сохранения сообщения.")
            return
    
    try:
        message_info = get_message_info(message)

        if not message_info:
            await message.reply_text("❌ Неподдерживаемый тип сообщения.")
            return
        
        # Проверяем медиа-файлы
        if message_info['type'] != 'text' and not config.get('принимать-медиа'):
            await message.reply_text("🚫 Отправка медиа-файлов отключена. Отправьте текстовое сообщение.")
            return
        
        BotLogger.log(f"📨 Получено сообщение от {user.id} (@{user.username}): {message_info['type']}")
        
        keyboard = [[InlineKeyboardButton("📤 Опубликовать в канал", callback_data="publish")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Формируем информацию об авторе
        author_info = f"@{user.username}" if user.username else user.first_name or "пользователя"
        
        sent_message = await send_message_to_group(context, message_info, author_info, reply_markup)
        
        storage.store_message(
            group_message_id=sent_message.message_id,
            user_id=user.id,
            message_data=message_info,
            username=user.username or user.first_name
        )
        
        await message.reply_text("✅ Ваше сообщение отправлено на рассмотрение!")
        BotLogger.log(f"✅ Сообщение от {user.id} успешно отправлено в группу")
        
    except Exception as e:
        logger.error(f"Ошибка при пересылке сообщения: {e}")
        await message.reply_text("❌ Произошла ошибка при отправке сообщения.")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Обработка кнопок настройки
    if query.data.startswith("config_"):
        if not is_admin(user_id):
            await query.edit_message_text("❌ У вас нет прав для настройки бота.")
            return
        
        config_key = query.data.replace("config_", "")
        current_value = config.get(config_key)
        
        if isinstance(current_value, bool):
            new_value = not current_value
            config.set(config_key, new_value)
            
            # Обновляем сообщение с новыми кнопками
            keyboard = get_config_keyboard()
            await query.edit_message_reply_markup(reply_markup=keyboard)
        
        return
    
    # Обработка подтверждения перезагрузки
    if query.data == "confirm_reboot":
        if user_id not in reboot_confirmation:
            await query.edit_message_text("❌ Сессия подтверждения истекла.")
            return
        
        del reboot_confirmation[user_id]
        BotLogger.log(f"🔄 Админ {user_id} инициировал перезагрузку бота")
        
        # Сохраняем информацию о перезагрузке
        RebootState.save_reboot_info(
            query.message.chat_id,
            query.message.message_id,
            user_id
        )
        
        await query.edit_message_text("🔄 Перезагружаю бота...")
        
        # Перезапускаем процесс
        os.execv(sys.executable, [sys.executable] + sys.argv)
    
    if query.data == "cancel_reboot":
        if user_id in reboot_confirmation:
            del reboot_confirmation[user_id]
        await query.edit_message_text("❌ Перезагрузка отменена.")
        return
    
    # Обработка публикации в канал
    if query.data == "publish":
        message_id = query.message.message_id
        stored_data = storage.get_message_data(message_id)
        
        if not stored_data:
            await query.edit_message_text("❌ Данные о сообщении не найдены.")
            return
        
        message_data = stored_data['message_data']
        user_id = stored_data['user_id']
        
        try:
            await send_message_to_channel(context, message_data)
            
            BotLogger.log(f"📺 Сообщение от {user_id} опубликовано в канале")
            
            await context.bot.send_message(
                chat_id=user_id,
                text="🎉 Ваше сообщение опубликовано!"
            )
            
            await context.bot.delete_message(
                chat_id=config.get('айди-группы'),
                message_id=message_id
            )
            
            storage.remove_message(message_id)
            
        except Exception as e:
            logger.error(f"Ошибка при публикации: {e}")
            await query.edit_message_text("❌ Произошла ошибка при публикации.")

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений в группе"""
    message = update.message
    user = update.effective_user
    
    # Проверяем ответы на сообщения бота
    if message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id:
        replied_message_id = message.reply_to_message.message_id
        stored_data = storage.get_message_data(replied_message_id)
        
        if stored_data:
            original_author_id = stored_data['user_id']
            
            # Формируем текст ответа
            if config.get('анонимные-ответы'):
                reply_text = f"💬 Анонимный комментарий к вашему сообщению:\n\n"
            else:
                commenter = f"@{user.username}" if user.username else user.first_name or "Аноним"
                reply_text = f"💬 Комментарий от {commenter}:\n\n"
            
            reply_text += message.text or "📎 Медиа-файл"
            
            try:
                await context.bot.send_message(
                    chat_id=original_author_id,
                    text=reply_text
                )
                
                BotLogger.log(f"💬 Комментарий от {user.id} отправлен пользователю {original_author_id}")
                
                confirm_text = "✅ Ваш анонимный комментарий отправлен!" if config.get('анонимные-ответы') else "✅ Ваш комментарий отправлен автору!"
                confirmation = await message.reply_text(confirm_text)
                
                # Удаляем сообщения
                try:
                    await context.bot.delete_message(
                        chat_id=config.get('айди-группы'),
                        message_id=message.message_id
                    )
                    
                    await asyncio.sleep(3)
                    await context.bot.delete_message(
                        chat_id=config.get('айди-группы'),
                        message_id=confirmation.message_id
                    )
                except:
                    pass
                    
            except Exception as e:
                logger.error(f"Ошибка при отправке ответа: {e}")
                await message.reply_text("❌ Не удалось отправить комментарий.")

def get_config_keyboard():
    """Создает клавиатуру для настройки конфигурации"""
    keyboard = []
    
    config_items = [
        ("принимать-сообщения", "📝 Приём сообщений"),
        ("принимать-медиа", "📸 Приём медиа"),
        ("рассылки-включены", "📢 Рассылки"),
        ("заглушка-включена", "🔇 Заглушка"),
        ("анонимные-авторы", "🕶 Анонимные авторы"),
        ("анонимные-ответы", "🎭 Анонимные ответы")
    ]
    
    for config_key, display_name in config_items:
        current_value = config.get(config_key)
        status = "✅" if current_value else "❌"
        button_text = f"{display_name}: {status}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"config_{config_key}")])
    
    return InlineKeyboardMarkup(keyboard)

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для просмотра базы пользователей (только для админов)"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для просмотра базы пользователей.")
        return
    
    all_users = user_storage.get_all_users()
    
    if not all_users:
        await update.message.reply_text("📭 База пользователей пуста.")
        return
    
    users_text = f"👥 База пользователей ({len(all_users)}):\n\n"
    
    for i, user_data in enumerate(all_users, 1):
        username = user_data.get('username', 'нет')
        first_name = user_data.get('first_name', 'нет')
        users_text += f"{i}. ID: {user_data['user_id']}\n"
        users_text += f"   @{username} | {first_name}\n\n"
        
        # Ограничиваем длину сообщения
        if len(users_text) > 3500:
            users_text += f"... и ещё {len(all_users) - i} пользователей"
            break
    
    await update.message.reply_text(users_text)

async def mailing_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для рассылки через бота"""
    user_id = update.effective_user.id
    
    print(f"🔍 Команда /mailing от пользователя {user_id}")
    print(f"🔍 Админы: {config.get('админы')}")
    print(f"🔍 Рассылки включены: {config.get('рассылки-включены')}")
    
    if not config.get('рассылки-включены'):
        await update.message.reply_text("🚫 Рассылка отключена.")
        return
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для рассылки.")
        print(f"❌ Пользователь {user_id} не является админом")
        return
    
    # Показываем количество пользователей
    all_users = user_storage.get_all_users()
    user_count = len(all_users)
    
    if user_count == 0:
        await update.message.reply_text("❌ Нет пользователей для рассылки.")
        return
    
    mailing_state[user_id] = True
    print(f"✅ Пользователь {user_id} активировал режим рассылки")
    print(f"🔍 Новое состояние: {mailing_state}")
    
    await update.message.reply_text(
        f"📢 Режим рассылки активирован!\n\n"
        f"👥 Пользователей в базе: {user_count}\n\n"
        f"📝 Отправьте следующее сообщение (текст, фото, видео, файл), и оно будет разослано всем пользователям бота."
    )

async def archive_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для получения логов за сегодняшний день"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для просмотра архива логов.")
        return
    
    today_logs = BotLogger.get_today_logs()
    
    if today_logs == "📭 Логов за сегодня нет.":
        await update.message.reply_text(today_logs)
        return
    
    # Если логи слишком длинные, отправляем файлом
    if len(today_logs) > 4000:
        try:
            # Создаем временный файл с логами
            temp_filename = f"logs_{datetime.now().strftime('%Y-%m-%d')}.txt"
            with open(temp_filename, 'w', encoding='utf-8') as f:
                f.write(today_logs)
            
            # Отправляем файл
            with open(temp_filename, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=temp_filename,
                    caption=f"📋 Логи за {datetime.now().strftime('%Y-%m-%d')}"
                )
            
            # Удаляем временный файл
            os.remove(temp_filename)
            
        except Exception as e:
            logger.error(f"Ошибка отправки файла логов: {e}")
            await update.message.reply_text("❌ Ошибка при создании файла логов.")
    else:
        await update.message.reply_text(f"📋 Логи за сегодня:\n\n{today_logs}")

async def configure_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для настройки бота через кнопки"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для настройки бота.")
        return
    
    keyboard = get_config_keyboard()
    
    config_text = "⚙️ Настройки бота:\n\n"
    config_text += "Нажмите на кнопку, чтобы переключить настройку:"
    
    await update.message.reply_text(config_text, reply_markup=keyboard)

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для включения/выключения режима заглушки"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для управления заглушкой.")
        return
    
    current_mute = config.get('заглушка-включена')
    new_mute = not current_mute
    
    if new_mute:
        # Включаем заглушку
        config.set('заглушка-включена', True)
        await update.message.reply_text(
            "🔇 Заглушка включена!\n\n"
            "Все сообщения от пользователей будут сохраняться в очереди и обработаются после выключения заглушки."
        )
        BotLogger.log(f"🔇 Админ {user_id} включил заглушку")
    else:
        # Выключаем заглушку
        config.set('заглушка-включена', False)
        
        # Обрабатываем накопившиеся сообщения
        queued_count = len(mute_queue.queue)
        
        await update.message.reply_text(
            f"🔊 Заглушка выключена!\n\n"
            f"Обрабатываю {queued_count} сообщений из очереди..."
        )
        
        BotLogger.log(f"🔊 Админ {user_id} выключил заглушку, в очереди {queued_count} сообщений")
        
        # Обрабатываем очередь
        await process_queued_messages(context)
        
        await update.message.reply_text("✅ Все сообщения из очереди обработаны!")

async def reboot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для перезагрузки бота с подтверждением"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для перезагрузки бота.")
        return
    
    # Сохраняем состояние подтверждения
    reboot_confirmation[user_id] = True
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, перезагрузить", callback_data="confirm_reboot"),
            InlineKeyboardButton("❌ Отменить", callback_data="cancel_reboot")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔄 Подтвердите перезагрузку бота\n\n"
        "⚠️ Все текущие операции будут прерваны.\n"
        "Бот перезапустится автоматически.",
        reply_markup=reply_markup
    )

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для бана пользователя (ответом на сообщение в группе)"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для бана пользователей.")
        return
    
    # Проверяем, что команда используется в ответ на сообщение
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Используйте команду в ответ на сообщение пользователя.")
        return
    
    # Получаем ID сообщения в группе
    replied_message_id = update.message.reply_to_message.message_id
    stored_data = storage.get_message_data(replied_message_id)
    
    if not stored_data:
        await update.message.reply_text("❌ Не удалось найти данные об авторе сообщения.")
        return
    
    banned_user_id = stored_data['user_id']
    banned_username = stored_data['username']
    
    # Получаем причину бана из аргументов команды
    reason = ' '.join(context.args) if context.args else "Не указана"
    
    # Баним пользователя
    banned_users.ban_user(banned_user_id, banned_username, reason)
    
    # Уведомляем о бане
    await update.message.reply_text(
        f"🚫 Пользователь {banned_user_id} (@{banned_username}) заблокирован.\n"
        f"📝 Причина: {reason}"
    )
    
    # Уведомляем самого пользователя
    try:
        await context.bot.send_message(
            chat_id=banned_user_id,
            text=f"🚫 Вы были заблокированы в боте.\n📝 Причина: {reason}"
        )
    except:
        pass  # Пользователь мог заблокировать бота

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для разбана пользователя"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для разбана пользователей.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Укажите ID пользователя для разбана.\nПример: /unban 123456789")
        return
    
    try:
        unban_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID пользователя.")
        return
    
    if banned_users.unban_user(unban_user_id):
        await update.message.reply_text(f"✅ Пользователь {unban_user_id} разблокирован.")
        
        # Уведомляем пользователя
        try:
            await context.bot.send_message(
                chat_id=unban_user_id,
                text="✅ Вы были разблокированы в боте. Теперь вы можете отправлять сообщения."
            )
        except:
            pass
    else:
        await update.message.reply_text("❌ Пользователь не найден в списке заблокированных.")

async def banlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для просмотра списка заблокированных пользователей"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для просмотра списка заблокированных.")
        return
    
    banned_list = banned_users.get_all_banned()
    
    if not banned_list:
        await update.message.reply_text("📋 Список заблокированных пуст.")
        return
    
    ban_text = f"🚫 Заблокированные пользователи ({len(banned_list)}):\n\n"
    
    for i, banned_user in enumerate(banned_list, 1):
        username = banned_user.get('username', 'нет')
        reason = banned_user.get('reason', 'Не указана')
        ban_date = datetime.fromtimestamp(banned_user.get('banned_at', 0)).strftime('%Y-%m-%d %H:%M')
        
        ban_text += f"{i}. ID: {banned_user['user_id']}\n"
        ban_text += f"   @{username}\n"
        ban_text += f"   📝 Причина: {reason}\n"
        ban_text += f"   📅 Дата: {ban_date}\n\n"
        
        # Ограничиваем длину сообщения
        if len(ban_text) > 3500:
            ban_text += f"... и ещё {len(banned_list) - i} пользователей"
            break
    
    await update.message.reply_text(ban_text)

def main():
    """Запуск бота"""
    # Проверяем, была ли перезагрузка
    reboot_info = RebootState.get_and_clear_reboot_info()
    
    application = Application.builder().token(config.get('токен-бота')).build()
    job_queue = JobQueue()
    job_queue.set_application(application)
    job_queue.start()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mailing", mailing_command))
    application.add_handler(CommandHandler("users", users_command))
    application.add_handler(CommandHandler("archive", archive_command))
    application.add_handler(CommandHandler("configure", configure_command))
    application.add_handler(CommandHandler("mute", mute_command))
    application.add_handler(CommandHandler("reboot", reboot_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("banlist", banlist_command))
    
    # ЕДИНЫЙ обработчик всех сообщений в приватном чате
    application.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL | 
         filters.ANIMATION | filters.VOICE | filters.AUDIO) & 
        filters.ChatType.PRIVATE & ~filters.COMMAND,
        handle_mailing_or_regular_message
    ))
    
    # Обработчик группы (только ответы)
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.REPLY, 
        handle_group_message
    ))
    
    # Callback обработчик
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Уведомляем о перезагрузке
    if reboot_info:
        application.job_queue.run_once(
            lambda context: asyncio.create_task(notify_reboot_complete(application, reboot_info)),
            when=2
        )

    # Запуск
    BotLogger.log("🚀 Бот запущен")
    print("🤖 Бот запущен с настройками:")
    print(f"📝 Приём сообщений: {'✅' if config.get('принимать-сообщения') else '❌'}")
    print(f"📸 Приём медиа: {'✅' if config.get('принимать-медиа') else '❌'}")
    print(f"🕶 Анонимные авторы: {'✅' if config.get('анонимные-авторы') else '❌'}")
    print(f"🕶 Анонимные ответы: {'✅' if config.get('анонимные-ответы') else '❌'}")
    print(f"📢 Рассылка: {'✅' if config.get('рассылки-включены') else '❌'}")
    print(f"🔇 Заглушка: {'✅' if config.get('заглушка-включена') else '❌'}")
    print(f"🚫 Забанено пользователей: {len(banned_users.get_all_banned())}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

async def setup_reboot_notification():
    if reboot_info:
        await notify_reboot_complete(application, reboot_info)
# Запуск
    BotLogger.log("🚀 Бот запущен")
    print("🤖 Бот запущен с настройками:")
    print(f"📝 Приём сообщений: {'✅' if config.get('принимать-сообщения') else '❌'}")
    print(f"📸 Приём медиа: {'✅' if config.get('принимать-медиа') else '❌'}")
    print(f"🕶 Анонимные авторы: {'✅' if config.get('анонимные-авторы') else '❌'}")
    print(f"🕶 Анонимные ответы: {'✅' if config.get('анонимные-ответы') else '❌'}")
    print(f"📢 Рассылка: {'✅' if config.get('рассылки-включены') else '❌'}")
    print(f"🔇 Заглушка: {'✅' if config.get('заглушка-включена') else '❌'}")
    print(f"🚫 Забанено пользователей: {len(banned_users.get_all_banned())}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

async def notify_reboot_complete(application, reboot_info):
    """Уведомляет о завершении перезагрузки"""
    try:
        # Ждем инициализации бота
        await asyncio.sleep(2)
        
        await application.bot.edit_message_text(
            chat_id=reboot_info['chat_id'],
            message_id=reboot_info['message_id'],
            text="✅ Бот успешно перезагружен!\n\n🤖 Все системы работают."
        )
        
        BotLogger.log(f"✅ Уведомление о перезагрузке отправлено админу {reboot_info['admin_id']}")
        
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления о перезагрузке: {e}")

if __name__ == '__main__':
    main()
