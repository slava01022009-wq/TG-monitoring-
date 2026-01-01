"""
Модуль конфигурации приложения
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Базовые пути
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
MEDIA_DIR = BASE_DIR / "media"
SESSION_DIR = BASE_DIR / "sessions"
DB_PATH = BASE_DIR / "telegram_monitor.db"

# Создание необходимых директорий
LOGS_DIR.mkdir(exist_ok=True)
MEDIA_DIR.mkdir(exist_ok=True)
SESSION_DIR.mkdir(exist_ok=True)

class Config:
    """Класс для управления конфигурацией"""
    
    def __init__(self):
        api_id_str = os.getenv("API_ID") or ""
        self.api_id = int(api_id_str) if api_id_str and api_id_str.isdigit() else ""
        self.api_hash = os.getenv("API_HASH") or ""
        self.phone = os.getenv("PHONE") or ""
        self.session_name = "telegram_monitor"
        self.session_path = str(SESSION_DIR / f"{self.session_name}.session")
        
        # Настройки логирования
        self.log_level = "INFO"
        self.log_to_file = True
        self.log_to_console = True
        self.log_json = True
        
        # Настройки мониторинга
        self.save_media = True
        self.monitor_messages = True
        self.monitor_reactions = True
        self.monitor_events = True
        self.monitor_media = True
        self.monitor_contacts = True
        self.monitor_groups = True
        
        # Настройки базы данных
        self.db_path = str(DB_PATH)
        
    def load_from_file(self, config_path="config.json"):
        """Загрузка конфигурации из файла"""
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.api_id = data.get("api_id", self.api_id)
                    self.api_hash = data.get("api_hash", self.api_hash)
                    self.phone = data.get("phone", self.phone)
                    if isinstance(self.api_id, str):
                        self.api_id = int(self.api_id) if self.api_id.isdigit() else ""
            except Exception as e:
                print(f"Ошибка загрузки конфигурации: {e}")
    
    def save_to_file(self, config_path="config.json"):
        """Сохранение конфигурации в файл"""
        try:
            data = {
                "api_id": str(self.api_id),
                "api_hash": self.api_hash,
                "phone": self.phone
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения конфигурации: {e}")
    
    def validate(self):
        """Проверка валидности конфигурации"""
        errors = []
        if not self.api_id:
            errors.append("API ID не указан")
        if not self.api_hash:
            errors.append("API HASH не указан")
        try:
            if self.api_id:
                int(self.api_id)
        except:
            errors.append("API ID должен быть числом")
        return errors

# Глобальный экземпляр конфигурации
config = Config()

