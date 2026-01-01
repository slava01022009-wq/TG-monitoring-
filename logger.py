"""
Модуль логирования
"""
import logging
import json
import os
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Dict, Any
from config import LOGS_DIR

class ColoredFormatter(logging.Formatter):
    """Форматтер с цветным выводом для консоли"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',        # Green
        'WARNING': '\033[33m',     # Yellow
        'ERROR': '\033[31m',       # Red
        'CRITICAL': '\033[35m',    # Magenta
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)

class JSONFormatter(logging.Formatter):
    """JSON форматтер для структурированного логирования"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        if hasattr(record, 'event_data'):
            log_data['event_data'] = record.event_data
        
        return json.dumps(log_data, ensure_ascii=False)

class AppLogger:
    """Класс для управления логированием"""
    
    def __init__(self, name: str = "TelegramMonitor"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Очистка существующих обработчиков
        self.logger.handlers.clear()
        
        # Консольный обработчик отключен - все логи идут через GUI
        # console_handler = logging.StreamHandler()
        # console_handler.setLevel(logging.INFO)
        # console_formatter = ColoredFormatter(
        #     '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        #     datefmt='%Y-%m-%d %H:%M:%S'
        # )
        # console_handler.setFormatter(console_formatter)
        # self.logger.addHandler(console_handler)
        
        # Файловый обработчик (текстовый)
        text_log_path = LOGS_DIR / f"{name.lower()}.log"
        file_handler = RotatingFileHandler(
            text_log_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # JSON обработчик
        json_log_path = LOGS_DIR / f"{name.lower()}_json.log"
        json_handler = RotatingFileHandler(
            json_log_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        json_handler.setLevel(logging.DEBUG)
        json_formatter = JSONFormatter()
        json_handler.setFormatter(json_formatter)
        self.logger.addHandler(json_handler)
        
        # Специализированные обработчики для разных типов событий
        self._setup_event_loggers()
    
    def _setup_event_loggers(self):
        """Настройка специализированных логгеров для событий"""
        event_types = ['messages', 'reactions', 'events', 'media']
        
        for event_type in event_types:
            event_log_path = LOGS_DIR / f"{event_type}.log"
            event_handler = RotatingFileHandler(
                event_log_path,
                maxBytes=10*1024*1024,
                backupCount=5,
                encoding='utf-8'
            )
            event_handler.setLevel(logging.INFO)
            event_formatter = logging.Formatter(
                '%(asctime)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            event_handler.setFormatter(event_formatter)
            
            event_logger = logging.getLogger(f"{self.logger.name}.{event_type}")
            event_logger.addHandler(event_handler)
            event_logger.setLevel(logging.INFO)
            event_logger.propagate = False
    
    def log_message(self, data: Dict[str, Any]):
        """Логирование сообщения"""
        event_logger = logging.getLogger(f"{self.logger.name}.messages")
        message = (
            f"[MESSAGE] Chat: {data.get('chat_title', 'Unknown')} | "
            f"From: {data.get('sender_username', data.get('sender_first_name', 'Unknown'))} | "
            f"Text: {data.get('text', '')[:100]} | "
            f"Outgoing: {data.get('is_outgoing', False)}"
        )
        event_logger.info(message)
        self.logger.debug(f"Message logged: {data.get('message_id')}")
    
    def log_reaction(self, data: Dict[str, Any]):
        """Логирование реакции"""
        event_logger = logging.getLogger(f"{self.logger.name}.reactions")
        message = (
            f"[REACTION] User: {data.get('user_username', 'Unknown')} | "
            f"Reaction: {data.get('reaction', 'Unknown')} | "
            f"Message ID: {data.get('message_id')} | "
            f"Action: {data.get('action', 'added')}"
        )
        event_logger.info(message)
        self.logger.debug(f"Reaction logged: {data.get('reaction')}")
    
    def log_event(self, data: Dict[str, Any]):
        """Логирование события"""
        event_logger = logging.getLogger(f"{self.logger.name}.events")
        message = (
            f"[EVENT] Type: {data.get('event_type', 'Unknown')} | "
            f"Chat: {data.get('chat_title', 'Unknown')} | "
            f"User: {data.get('user_username', data.get('user_first_name', 'Unknown'))} | "
            f"Details: {data.get('details', {})}"
        )
        event_logger.info(message)
        self.logger.debug(f"Event logged: {data.get('event_type')}")
    
    def log_media(self, data: Dict[str, Any]):
        """Логирование медиа"""
        event_logger = logging.getLogger(f"{self.logger.name}.media")
        message = (
            f"[MEDIA] Type: {data.get('media_type', 'Unknown')} | "
            f"File: {data.get('file_name', 'Unknown')} | "
            f"Size: {data.get('file_size', 0)} bytes"
        )
        event_logger.info(message)
        self.logger.debug(f"Media logged: {data.get('file_name')}")
    
    def get_logger(self):
        """Получение основного логгера"""
        return self.logger

# Глобальный экземпляр логгера
app_logger = AppLogger()
logger = app_logger.get_logger()

