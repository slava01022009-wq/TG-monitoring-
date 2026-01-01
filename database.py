"""
Модуль для работы с базой данных
"""
import sqlite3
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class Database:
    """Класс для работы с SQLite базой данных"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.lock = asyncio.Lock()
        self._init_database()
    
    def _init_database(self):
        """Инициализация базы данных и создание таблиц"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            cursor = self.conn.cursor()
            
            # Таблица сообщений
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER,
                    chat_id INTEGER,
                    chat_title TEXT,
                    sender_id INTEGER,
                    sender_username TEXT,
                    sender_first_name TEXT,
                    sender_last_name TEXT,
                    text TEXT,
                    is_outgoing INTEGER,
                    is_edited INTEGER,
                    is_deleted INTEGER,
                    is_forwarded INTEGER,
                    forward_from_id INTEGER,
                    media_type TEXT,
                    media_path TEXT,
                    date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица реакций
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER,
                    chat_id INTEGER,
                    user_id INTEGER,
                    user_username TEXT,
                    reaction TEXT,
                    action TEXT,
                    date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица событий
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT,
                    chat_id INTEGER,
                    chat_title TEXT,
                    user_id INTEGER,
                    user_username TEXT,
                    user_first_name TEXT,
                    details TEXT,
                    date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица медиа
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS media (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER,
                    chat_id INTEGER,
                    media_type TEXT,
                    file_name TEXT,
                    file_path TEXT,
                    file_size INTEGER,
                    mime_type TEXT,
                    date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица контактов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    phone TEXT,
                    action TEXT,
                    date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица групп
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    chat_title TEXT,
                    action TEXT,
                    user_id INTEGER,
                    user_username TEXT,
                    details TEXT,
                    date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Создание индексов
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_date ON messages(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reactions_message_id ON reactions(message_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_date ON events(date)")
            
            self.conn.commit()
            logger.info("База данных инициализирована")
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise
    
    async def insert_message(self, data: Dict[str, Any]):
        """Вставка сообщения в БД"""
        async with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT INTO messages (
                        message_id, chat_id, chat_title, sender_id, sender_username,
                        sender_first_name, sender_last_name, text, is_outgoing,
                        is_edited, is_deleted, is_forwarded, forward_from_id,
                        media_type, media_path, date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get('message_id'),
                    data.get('chat_id'),
                    data.get('chat_title'),
                    data.get('sender_id'),
                    data.get('sender_username'),
                    data.get('sender_first_name'),
                    data.get('sender_last_name'),
                    data.get('text', ''),
                    data.get('is_outgoing', 0),
                    data.get('is_edited', 0),
                    data.get('is_forwarded', 0),
                    data.get('forward_from_id'),
                    data.get('media_type'),
                    data.get('media_path'),
                    data.get('date')
                ))
                self.conn.commit()
                return cursor.lastrowid
            except Exception as e:
                logger.error(f"Ошибка вставки сообщения: {e}")
                self.conn.rollback()
                return None
    
    async def insert_reaction(self, data: Dict[str, Any]):
        """Вставка реакции в БД"""
        async with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT INTO reactions (
                        message_id, chat_id, user_id, user_username,
                        reaction, action, date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get('message_id'),
                    data.get('chat_id'),
                    data.get('user_id'),
                    data.get('user_username'),
                    data.get('reaction'),
                    data.get('action', 'added'),
                    data.get('date')
                ))
                self.conn.commit()
                return cursor.lastrowid
            except Exception as e:
                logger.error(f"Ошибка вставки реакции: {e}")
                self.conn.rollback()
                return None
    
    async def insert_event(self, data: Dict[str, Any]):
        """Вставка события в БД"""
        async with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT INTO events (
                        event_type, chat_id, chat_title, user_id,
                        user_username, user_first_name, details, date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get('event_type'),
                    data.get('chat_id'),
                    data.get('chat_title'),
                    data.get('user_id'),
                    data.get('user_username'),
                    data.get('user_first_name'),
                    json.dumps(data.get('details', {}), ensure_ascii=False),
                    data.get('date')
                ))
                self.conn.commit()
                return cursor.lastrowid
            except Exception as e:
                logger.error(f"Ошибка вставки события: {e}")
                self.conn.rollback()
                return None
    
    async def insert_media(self, data: Dict[str, Any]):
        """Вставка медиа в БД"""
        async with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT INTO media (
                        message_id, chat_id, media_type, file_name,
                        file_path, file_size, mime_type, date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get('message_id'),
                    data.get('chat_id'),
                    data.get('media_type'),
                    data.get('file_name'),
                    data.get('file_path'),
                    data.get('file_size'),
                    data.get('mime_type'),
                    data.get('date')
                ))
                self.conn.commit()
                return cursor.lastrowid
            except Exception as e:
                logger.error(f"Ошибка вставки медиа: {e}")
                self.conn.rollback()
                return None
    
    async def insert_contact(self, data: Dict[str, Any]):
        """Вставка контакта в БД"""
        async with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT INTO contacts (
                        user_id, username, first_name, last_name,
                        phone, action, date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get('user_id'),
                    data.get('username'),
                    data.get('first_name'),
                    data.get('last_name'),
                    data.get('phone'),
                    data.get('action'),
                    data.get('date')
                ))
                self.conn.commit()
                return cursor.lastrowid
            except Exception as e:
                logger.error(f"Ошибка вставки контакта: {e}")
                self.conn.rollback()
                return None
    
    async def insert_group_event(self, data: Dict[str, Any]):
        """Вставка события группы в БД"""
        async with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT INTO groups (
                        chat_id, chat_title, action, user_id,
                        user_username, details, date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get('chat_id'),
                    data.get('chat_title'),
                    data.get('action'),
                    data.get('user_id'),
                    data.get('user_username'),
                    json.dumps(data.get('details', {}), ensure_ascii=False),
                    data.get('date')
                ))
                self.conn.commit()
                return cursor.lastrowid
            except Exception as e:
                logger.error(f"Ошибка вставки события группы: {e}")
                self.conn.rollback()
                return None
    
    def get_statistics(self) -> Dict[str, int]:
        """Получение статистики"""
        try:
            cursor = self.conn.cursor()
            stats = {}
            cursor.execute("SELECT COUNT(*) FROM messages")
            stats['messages'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM reactions")
            stats['reactions'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM events")
            stats['events'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM media")
            stats['media'] = cursor.fetchone()[0]
            return stats
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}
    
    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Получение последних событий"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 'message' as type, date, chat_title, sender_username, text as content
                FROM messages
                UNION ALL
                SELECT 'reaction' as type, date, '' as chat_title, user_username, reaction as content
                FROM reactions
                UNION ALL
                SELECT 'event' as type, date, chat_title, user_username, event_type as content
                FROM events
                ORDER BY date DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка получения событий: {e}")
            return []
    
    def close(self):
        """Закрытие соединения с БД"""
        if self.conn:
            self.conn.close()

