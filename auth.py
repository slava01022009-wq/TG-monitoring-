"""
Модуль авторизации в Telegram
"""
import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from typing import Optional, Callable
from config import config
from logger import logger
import inspect

class TelegramAuth:
    """Класс для авторизации в Telegram"""
    
    def __init__(self, api_id: int, api_hash: str, session_path: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_path = session_path
        self.client: Optional[TelegramClient] = None
        self.phone_code_callback: Optional[Callable] = None
        self.password_callback: Optional[Callable] = None
    
    def set_phone_code_callback(self, callback: Callable):
        """Установка callback для ввода кода из SMS"""
        self.phone_code_callback = callback
    
    def set_password_callback(self, callback: Callable):
        """Установка callback для ввода облачного пароля"""
        self.password_callback = callback
    
    async def connect(self) -> bool:
        """Подключение к Telegram"""
        try:
            self.client = TelegramClient(
                self.session_path,
                self.api_id,
                self.api_hash,
                device_model="Telegram Monitor",
                system_version="1.0",
                app_version="1.0.0"
            )
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                logger.warning("Пользователь не авторизован")
                return False
            
            logger.info("Успешное подключение к Telegram")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            return False
    
    async def authorize(self, phone: str) -> bool:
        """Авторизация по номеру телефона"""
        try:
            if not self.client:
                await self.connect()
            
            if await self.client.is_user_authorized():
                logger.info("Уже авторизован")
                return True
            
            logger.info(f"Отправка кода на номер: {phone}")
            await self.client.send_code_request(phone)
            
            # Запрос кода
            if not self.phone_code_callback:
                raise ValueError("Callback для кода не установлен")
            
            # Вызов callback (может быть синхронным или асинхронным)
            if inspect.iscoroutinefunction(self.phone_code_callback):
                code = await self.phone_code_callback()
            else:
                code = self.phone_code_callback()
            
            if not code:
                logger.error("Код не введен")
                return False
            
            try:
                # Попытка авторизации с кодом
                await self.client.sign_in(phone, code)
                logger.info("Успешная авторизация")
                return True
            except SessionPasswordNeededError:
                # Требуется облачный пароль
                logger.info("Требуется облачный пароль (2FA)")
                if not self.password_callback:
                    raise ValueError("Callback для пароля не установлен")
                
                # Вызов callback (может быть синхронным или асинхронным)
                if inspect.iscoroutinefunction(self.password_callback):
                    password = await self.password_callback()
                else:
                    password = self.password_callback()
                
                if not password:
                    logger.error("Пароль не введен")
                    return False
                
                await self.client.sign_in(password=password)
                logger.info("Успешная авторизация с паролем")
                return True
            except PhoneCodeInvalidError:
                logger.error("Неверный код")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка авторизации: {e}")
            return False
    
    def get_client(self) -> Optional[TelegramClient]:
        """Получение клиента Telegram"""
        return self.client
    
    async def disconnect(self):
        """Отключение от Telegram"""
        if self.client:
            await self.client.disconnect()
            logger.info("Отключено от Telegram")

