"""
Модуль мониторинга Telegram
"""
import asyncio
from datetime import datetime
from typing import Optional
from telethon import TelegramClient, events
from telethon.tl.types import (
    MessageService, MessageMediaPhoto, MessageMediaDocument,
    UserStatusOnline, UserStatusOffline, UserStatusRecently,
    User, Chat, Channel
)
from pathlib import Path
import aiofiles

from config import config, MEDIA_DIR
from database import Database
from logger import app_logger, logger

class TelegramMonitor:
    """Класс для мониторинга Telegram"""
    
    def __init__(self, client: TelegramClient, db: Database, event_callback=None):
        self.client = client
        self.db = db
        self.logger = app_logger
        self.event_callback = event_callback  # Callback для передачи событий в GUI
        self.stats = {
            'messages': 0,
            'reactions': 0,
            'events': 0,
            'media': 0,
            'contacts': 0,
            'groups': 0
        }
        self.running = False
        self.me = None  # Информация о себе
    
    async def start(self):
        """Запуск мониторинга"""
        self.running = True
        logger.info("Мониторинг запущен")
        
        # Получение информации о себе
        try:
            self.me = await self.client.get_me()
            logger.info(f"Мониторинг для: {self.me.first_name} (@{self.me.username or 'без username'})")
        except Exception as e:
            logger.error(f"Ошибка получения информации о себе: {e}")
        
        # Регистрация обработчиков
        self._register_handlers()
        
        # Запуск мониторинга статусов
        asyncio.create_task(self._monitor_user_statuses())
    
    def _register_handlers(self):
        """Регистрация всех обработчиков событий"""
        
        # Обработчик новых сообщений
        @self.client.on(events.NewMessage())
        async def handle_new_message(event):
            if config.monitor_messages:
                await self._handle_message(event)
        
        # Обработчик редактированных сообщений
        @self.client.on(events.MessageEdited())
        async def handle_edited_message(event):
            if config.monitor_messages:
                await self._handle_edited_message(event)
        
        # Обработчик удаленных сообщений
        @self.client.on(events.MessageDeleted())
        async def handle_deleted_message(event):
            if config.monitor_messages:
                await self._handle_deleted_message(event)
        
        # Обработчик реакций
        @self.client.on(events.MessageReactions())
        async def handle_reactions(event):
            if config.monitor_reactions:
                await self._handle_reactions(event)
        
        # Обработчик изменений в чатах
        @self.client.on(events.ChatAction())
        async def handle_chat_action(event):
            if config.monitor_events:
                await self._handle_chat_action(event)
        
        # Обработчик изменений пользователей
        @self.client.on(events.UserUpdate())
        async def handle_user_update(event):
            if config.monitor_contacts:
                await self._handle_user_update(event)
        
        logger.info("Все обработчики зарегистрированы")
    
    async def _handle_message(self, event):
        """Обработка нового сообщения"""
        try:
            message = event.message
            chat = await event.get_chat()
            sender = await event.get_sender()
            
            # Получение информации о чате
            chat_id = chat.id
            chat_title = getattr(chat, 'title', None) or getattr(chat, 'first_name', 'Unknown')
            
            # Определение типа чата
            chat_type = None
            if isinstance(chat, User):
                chat_type = 'private'
            elif isinstance(chat, Chat):
                chat_type = 'group'
            elif isinstance(chat, Channel):
                if chat.broadcast:
                    chat_type = 'channel'
                else:
                    chat_type = 'supergroup'
            else:
                chat_type = 'unknown'
            
            # Получение информации об отправителе
            sender_id = sender.id if sender else None
            sender_username = getattr(sender, 'username', None) if sender else None
            sender_first_name = getattr(sender, 'first_name', None) if sender else None
            sender_last_name = getattr(sender, 'last_name', None) if sender else None
            
            # Текст сообщения
            text = message.message or ""
            
            # Проверка на медиа
            media_type = None
            media_path = None
            
            if message.media:
                if isinstance(message.media, MessageMediaPhoto):
                    media_type = "photo"
                    if config.save_media and config.monitor_media:
                        media_path = await self._save_media(message, "photo")
                elif isinstance(message.media, MessageMediaDocument):
                    doc = message.media.document
                    if doc:
                        mime_type = doc.mime_type or ""
                        if mime_type.startswith('video/'):
                            media_type = "video"
                        elif mime_type.startswith('audio/'):
                            media_type = "audio"
                        elif mime_type.startswith('image/'):
                            media_type = "image"
                        else:
                            media_type = "document"
                        
                        if config.save_media and config.monitor_media:
                            media_path = await self._save_media(message, media_type)
            
            # Проверка на пересылку
            is_forwarded = message.fwd_from is not None
            forward_from_id = message.fwd_from.from_id.user_id if is_forwarded and message.fwd_from.from_id else None
            
            data = {
                'message_id': message.id,
                'chat_id': chat_id,
                'chat_title': chat_title,
                'chat_type': chat_type,
                'sender_id': sender_id,
                'sender_username': sender_username,
                'sender_first_name': sender_first_name,
                'sender_last_name': sender_last_name,
                'text': text,
                'is_outgoing': message.out,
                'is_edited': False,
                'is_deleted': False,
                'is_forwarded': is_forwarded,
                'forward_from_id': forward_from_id,
                'media_type': media_type,
                'media_path': media_path,
                'date': datetime.fromtimestamp(message.date.timestamp())
            }
            
            await self.db.insert_message(data)
            self.logger.log_message(data)
            self.stats['messages'] += 1
            
            # Отправка в GUI
            if self.event_callback:
                direction = "➡️ ИСХОДЯЩЕЕ" if message.out else "⬅️ ВХОДЯЩЕЕ"
                media_info = f" [{media_type}]" if media_type else ""
                sender_name = sender_first_name or sender_username or 'Unknown'
                text_preview = text[:50] if text else '[без текста]'
                chat_type_icon = {'private': '👤', 'group': '👥', 'supergroup': '👥', 'channel': '📢'}.get(chat_type, '❓')
                display_text = f"{direction} | {chat_type_icon} {chat_title} | {sender_name}: {text_preview}{media_info}"
                self.event_callback({
                    'type': 'message',
                    'data': data,
                    'display': display_text,
                    'chat_type': chat_type
                })
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
    
    async def _handle_edited_message(self, event):
        """Обработка отредактированного сообщения"""
        try:
            message = event.message
            chat = await event.get_chat()
            sender = await event.get_sender()
            
            chat_id = chat.id
            chat_title = getattr(chat, 'title', None) or getattr(chat, 'first_name', 'Unknown')
            
            # Определение типа чата
            chat_type = None
            if isinstance(chat, User):
                chat_type = 'private'
            elif isinstance(chat, Chat):
                chat_type = 'group'
            elif isinstance(chat, Channel):
                if chat.broadcast:
                    chat_type = 'channel'
                else:
                    chat_type = 'supergroup'
            else:
                chat_type = 'unknown'
            
            sender_id = sender.id if sender else None
            sender_username = getattr(sender, 'username', None) if sender else None
            sender_first_name = getattr(sender, 'first_name', None) if sender else None
            sender_last_name = getattr(sender, 'last_name', None) if sender else None
            
            data = {
                'message_id': message.id,
                'chat_id': chat_id,
                'chat_title': chat_title,
                'chat_type': chat_type,
                'sender_id': sender_id,
                'sender_username': sender_username,
                'sender_first_name': sender_first_name,
                'sender_last_name': sender_last_name,
                'text': message.message or "",
                'is_outgoing': message.out,
                'is_edited': True,
                'is_deleted': False,
                'is_forwarded': message.fwd_from is not None,
                'forward_from_id': None,
                'media_type': None,
                'media_path': None,
                'date': datetime.fromtimestamp(message.date.timestamp())
            }
            
            await self.db.insert_message(data)
            self.logger.log_message(data)
            self.stats['messages'] += 1
            
            # Отправка в GUI
            if self.event_callback:
                direction = "➡️ ИСХОДЯЩЕЕ" if message.out else "⬅️ ВХОДЯЩЕЕ"
                chat_type_icon = {'private': '👤', 'group': '👥', 'supergroup': '👥', 'channel': '📢'}.get(chat_type, '❓')
                display_text = f"✏️ РЕДАКТИРОВАНО | {direction} | {chat_type_icon} {chat_title} | {sender_first_name or sender_username or 'Unknown'}: {message.message[:50] if message.message else '[без текста]'}"
                self.event_callback({
                    'type': 'message_edited',
                    'data': data,
                    'display': display_text,
                    'chat_type': chat_type
                })
            
        except Exception as e:
            logger.error(f"Ошибка обработки отредактированного сообщения: {e}")
    
    async def _handle_deleted_message(self, event):
        """Обработка удаленного сообщения"""
        try:
            chat = await event.get_chat()
            chat_id = chat.id
            chat_title = getattr(chat, 'title', None) or getattr(chat, 'first_name', 'Unknown')
            
            # Определение типа чата
            chat_type = None
            if isinstance(chat, User):
                chat_type = 'private'
            elif isinstance(chat, Chat):
                chat_type = 'group'
            elif isinstance(chat, Channel):
                if chat.broadcast:
                    chat_type = 'channel'
                else:
                    chat_type = 'supergroup'
            else:
                chat_type = 'unknown'
            
            # Попытка получить информацию об удаленных сообщениях
            deleted_count = len(event.deleted_ids)
            
            for msg_id in event.deleted_ids:
                # Попытка получить информацию о сообщении из истории
                try:
                    # Получаем информацию о чате
                    messages = await self.client.get_messages(chat, limit=1)
                    # Пытаемся найти информацию о сообщении
                except:
                    pass
                
                data = {
                    'message_id': msg_id,
                    'chat_id': chat_id,
                    'chat_title': chat_title,
                    'chat_type': chat_type,
                    'sender_id': None,
                    'sender_username': None,
                    'sender_first_name': None,
                    'sender_last_name': None,
                    'text': f'[УДАЛЕНО - ID: {msg_id}]',
                    'is_outgoing': False,
                    'is_edited': False,
                    'is_deleted': True,
                    'is_forwarded': False,
                    'forward_from_id': None,
                    'media_type': None,
                    'media_path': None,
                    'date': datetime.now()
                }
                
                await self.db.insert_message(data)
                self.logger.log_message(data)
                self.stats['messages'] += 1
                
                # Отправка в GUI
                if self.event_callback:
                    chat_type_icon = {'private': '👤', 'group': '👥', 'supergroup': '👥', 'channel': '📢'}.get(chat_type, '❓')
                    display_text = f"🗑️ УДАЛЕНО | {chat_type_icon} {chat_title} | ID сообщения: {msg_id} | Время: {datetime.now().strftime('%H:%M:%S')}"
                    self.event_callback({
                        'type': 'message_deleted',
                        'data': data,
                        'display': display_text,
                        'chat_type': chat_type
                    })
                
        except Exception as e:
            logger.error(f"Ошибка обработки удаленного сообщения: {e}")
    
    async def _handle_reactions(self, event):
        """Обработка реакций"""
        try:
            message = event.message
            chat = await event.get_chat()
            chat_id = chat.id
            
            # Определение типа чата
            chat_type = None
            if isinstance(chat, User):
                chat_type = 'private'
            elif isinstance(chat, Chat):
                chat_type = 'group'
            elif isinstance(chat, Channel):
                if chat.broadcast:
                    chat_type = 'channel'
                else:
                    chat_type = 'supergroup'
            else:
                chat_type = 'unknown'
            
            if message.reactions:
                for reaction in message.reactions.results:
                    user_ids = reaction.recent_reactions or []
                    reaction_emoji = reaction.reaction.emoticon if hasattr(reaction.reaction, 'emoticon') else str(reaction.reaction)
                    
                    for recent in user_ids:
                        user_id = recent.peer_id.user_id if hasattr(recent.peer_id, 'user_id') else None
                        
                        try:
                            user = await self.client.get_entity(user_id) if user_id else None
                            user_username = getattr(user, 'username', None) if user else None
                        except:
                            user_username = None
                        
                        data = {
                            'message_id': message.id,
                            'chat_id': chat_id,
                            'user_id': user_id,
                            'user_username': user_username,
                            'reaction': reaction_emoji,
                            'action': 'added',
                            'date': datetime.now()
                        }
                        
                        await self.db.insert_reaction(data)
                        self.logger.log_reaction(data)
                        self.stats['reactions'] += 1
                        
                        # Отправка в GUI
                        if self.event_callback:
                            chat_type_icon = {'private': '👤', 'group': '👥', 'supergroup': '👥', 'channel': '📢'}.get(chat_type, '❓')
                            chat_title = getattr(chat, 'title', None) or getattr(chat, 'first_name', 'Unknown')
                            display_text = f"👍 РЕАКЦИЯ | {chat_type_icon} {chat_title} | {reaction_emoji} от {user_username or 'Unknown'} | Сообщение ID: {message.id}"
                            self.event_callback({
                                'type': 'reaction',
                                'data': data,
                                'display': display_text,
                                'chat_type': chat_type
                            })
                        
        except Exception as e:
            logger.error(f"Ошибка обработки реакций: {e}")
    
    async def _handle_chat_action(self, event):
        """Обработка действий в чате"""
        try:
            chat = await event.get_chat()
            user = await event.get_user()
            
            chat_id = chat.id
            chat_title = getattr(chat, 'title', None) or getattr(chat, 'first_name', 'Unknown')
            user_id = user.id if user else None
            user_username = getattr(user, 'username', None) if user else None
            user_first_name = getattr(user, 'first_name', None) if user else None
            
            event_type = None
            details = {}
            
            if event.user_joined:
                event_type = "user_joined"
            elif event.user_left:
                event_type = "user_left"
            elif event.user_added:
                event_type = "user_added"
            elif event.user_kicked:
                event_type = "user_kicked"
            elif event.user_banned:
                event_type = "user_banned"
            elif event.chat_title_changed:
                event_type = "chat_title_changed"
                details['new_title'] = event.new_title
            elif event.chat_photo_changed:
                event_type = "chat_photo_changed"
            elif event.pinned_message:
                event_type = "message_pinned"
                details['message_id'] = event.pinned_message.id
            
            if event_type:
                data = {
                    'event_type': event_type,
                    'chat_id': chat_id,
                    'chat_title': chat_title,
                    'user_id': user_id,
                    'user_username': user_username,
                    'user_first_name': user_first_name,
                    'details': details,
                    'date': datetime.now()
                }
                
                await self.db.insert_event(data)
                self.logger.log_event(data)
                self.stats['events'] += 1
                
                # Отправка в GUI
                if self.event_callback:
                    event_icons = {
                        'user_joined': '👋',
                        'user_left': '👋',
                        'user_added': '➕',
                        'user_kicked': '👢',
                        'user_banned': '🚫',
                        'chat_title_changed': '✏️',
                        'chat_photo_changed': '📷',
                        'message_pinned': '📌'
                    }
                    icon = event_icons.get(event_type, '📢')
                    chat_type_icon = {'private': '👤', 'group': '👥', 'supergroup': '👥', 'channel': '📢'}.get(chat_type, '❓')
                    display_text = f"{icon} {event_type.upper()} | {chat_type_icon} {chat_title} | {user_first_name or user_username or 'Unknown'}"
                    self.event_callback({
                        'type': 'chat_event',
                        'data': data,
                        'display': display_text,
                        'chat_type': chat_type
                    })
                
        except Exception as e:
            logger.error(f"Ошибка обработки действия в чате: {e}")
    
    async def _handle_user_update(self, event):
        """Обработка обновлений пользователя"""
        try:
            user = event.user
            if not user:
                return
            
            user_id = user.id
            username = getattr(user, 'username', None)
            first_name = getattr(user, 'first_name', None)
            last_name = getattr(user, 'last_name', None)
            phone = getattr(user, 'phone', None)
            
            # Определение типа изменения
            event_type = "user_updated"
            details = {
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone
            }
            
            data = {
                'event_type': event_type,
                'chat_id': None,
                'chat_title': None,
                'user_id': user_id,
                'user_username': username,
                'user_first_name': first_name,
                'details': details,
                'date': datetime.now()
            }
            
            await self.db.insert_event(data)
            self.logger.log_event(data)
            self.stats['events'] += 1
            
        except Exception as e:
            logger.error(f"Ошибка обработки обновления пользователя: {e}")
    
    async def _save_media(self, message, media_type: str) -> Optional[str]:
        """Сохранение медиа файла"""
        try:
            file_name = f"{message.id}_{media_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if media_type == "photo":
                file_path = MEDIA_DIR / f"{file_name}.jpg"
            else:
                file_path = MEDIA_DIR / f"{file_name}"
            
            await message.download_media(file=str(file_path))
            
            # Получение chat_id
            chat_id = None
            if hasattr(message.peer_id, 'channel_id'):
                chat_id = message.peer_id.channel_id
            elif hasattr(message.peer_id, 'user_id'):
                chat_id = message.peer_id.user_id
            elif hasattr(message.peer_id, 'chat_id'):
                chat_id = message.peer_id.chat_id
            
            # Сохранение информации о медиа в БД
            media_data = {
                'message_id': message.id,
                'chat_id': chat_id,
                'media_type': media_type,
                'file_name': file_path.name,
                'file_path': str(file_path),
                'file_size': file_path.stat().st_size if file_path.exists() else 0,
                'mime_type': None,
                'date': datetime.fromtimestamp(message.date.timestamp())
            }
            
            await self.db.insert_media(media_data)
            self.logger.log_media(media_data)
            self.stats['media'] += 1
            
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Ошибка сохранения медиа: {e}")
            return None
    
    async def _monitor_user_statuses(self):
        """Мониторинг статусов пользователей"""
        # Эта функция может быть расширена для отслеживания статусов
        pass
    
    def get_stats(self):
        """Получение статистики"""
        return self.stats.copy()
    
    def stop(self):
        """Остановка мониторинга"""
        self.running = False
        logger.info("Мониторинг остановлен")

