"""
Графический интерфейс приложения
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import asyncio
import threading
from datetime import datetime
from typing import Optional
import json

from config import config
from auth import TelegramAuth
from database import Database
from monitor import TelegramMonitor
from logger import logger

class TelegramMonitorGUI:
    """Графический интерфейс для мониторинга Telegram"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Monitor - Профессиональный мониторинг")
        self.root.geometry("1200x800")
        self.root.configure(bg='#2b2b2b')
        
        # Переменные состояния
        self.auth: Optional[TelegramAuth] = None
        self.monitor: Optional[TelegramMonitor] = None
        self.db: Optional[Database] = None
        self.client = None
        self.monitoring = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.loop_thread: Optional[threading.Thread] = None
        
        # Переменные для ввода
        self.phone_code_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.auth_dialog: Optional[tk.Toplevel] = None
        
        # Фильтры событий
        self.filters = {
            'messages': tk.BooleanVar(value=True),
            'my_messages': tk.BooleanVar(value=True),
            'deleted': tk.BooleanVar(value=True),
            'edited': tk.BooleanVar(value=True),
            'reactions': tk.BooleanVar(value=True),
            'events': tk.BooleanVar(value=True),
            'status': tk.BooleanVar(value=True),
            'media': tk.BooleanVar(value=True),
            # Фильтры по типам чатов
            'private': tk.BooleanVar(value=True),
            'group': tk.BooleanVar(value=True),
            'supergroup': tk.BooleanVar(value=True),
            'channel': tk.BooleanVar(value=True)
        }
        
        self._create_widgets()
        self._start_event_loop()
    
    def _create_widgets(self):
        """Создание виджетов интерфейса"""
        # Стиль
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#2b2b2b')
        style.configure('TLabel', background='#2b2b2b', foreground='#ffffff')
        style.configure('TButton', padding=10)
        
        # Главный контейнер
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Левая панель (настройки) с прокруткой
        left_panel_container = ttk.Frame(main_frame)
        left_panel_container.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        
        # Canvas для прокрутки
        left_canvas = tk.Canvas(left_panel_container, bg='#2b2b2b', highlightthickness=0)
        scrollbar_left = ttk.Scrollbar(left_panel_container, orient="vertical", command=left_canvas.yview)
        left_panel = ttk.Frame(left_canvas)
        
        left_panel.bind(
            "<Configure>",
            lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all"))
        )
        
        left_canvas.create_window((0, 0), window=left_panel, anchor="nw")
        left_canvas.configure(yscrollcommand=scrollbar_left.set)
        
        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_left.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Привязка прокрутки колесом мыши
        def _on_mousewheel(event):
            left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        left_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Правая панель (логи и статистика)
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # === ЛЕВАЯ ПАНЕЛЬ ===
        # Заголовок
        title_label = tk.Label(
            left_panel,
            text="⚙️ Настройки",
            font=("Arial", 14, "bold"),
            bg='#2b2b2b',
            fg='#4CAF50'
        )
        title_label.pack(pady=(5, 10))
        
        # API ID
        api_id_frame = ttk.Frame(left_panel)
        api_id_frame.pack(fill=tk.X, pady=5)
        tk.Label(
            api_id_frame,
            text="API ID:",
            bg='#2b2b2b',
            fg='#ffffff'
        ).pack(side=tk.LEFT)
        self.api_id_entry = tk.Entry(api_id_frame, width=30, bg='#3b3b3b', fg='#ffffff', insertbackground='#ffffff')
        self.api_id_entry.pack(side=tk.LEFT, padx=5)
        self.api_id_entry.insert(0, str(config.api_id) if config.api_id else "")
        
        # API HASH
        api_hash_frame = ttk.Frame(left_panel)
        api_hash_frame.pack(fill=tk.X, pady=5)
        tk.Label(
            api_hash_frame,
            text="API HASH:",
            bg='#2b2b2b',
            fg='#ffffff'
        ).pack(side=tk.LEFT)
        self.api_hash_entry = tk.Entry(api_hash_frame, width=30, bg='#3b3b3b', fg='#ffffff', insertbackground='#ffffff', show="*")
        self.api_hash_entry.pack(side=tk.LEFT, padx=5)
        self.api_hash_entry.insert(0, config.api_hash if config.api_hash else "")
        
        # Номер телефона
        phone_frame = ttk.Frame(left_panel)
        phone_frame.pack(fill=tk.X, pady=5)
        tk.Label(
            phone_frame,
            text="Телефон:",
            bg='#2b2b2b',
            fg='#ffffff'
        ).pack(side=tk.LEFT)
        self.phone_entry = tk.Entry(phone_frame, width=30, bg='#3b3b3b', fg='#ffffff', insertbackground='#ffffff')
        self.phone_entry.pack(side=tk.LEFT, padx=5)
        self.phone_entry.insert(0, config.phone if config.phone else "")
        
        # Кнопка подключения
        self.connect_btn = tk.Button(
            left_panel,
            text="🔌 Подключиться",
            command=self._connect,
            bg='#4CAF50',
            fg='#ffffff',
            font=("Arial", 12, "bold"),
            padx=20,
            pady=10,
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.connect_btn.pack(pady=20, fill=tk.X)
        
        # Кнопка запуска мониторинга
        self.monitor_btn = tk.Button(
            left_panel,
            text="▶️ Запустить мониторинг",
            command=self._toggle_monitoring,
            bg='#2196F3',
            fg='#ffffff',
            font=("Arial", 12, "bold"),
            padx=20,
            pady=10,
            relief=tk.FLAT,
            cursor="hand2",
            state=tk.DISABLED
        )
        self.monitor_btn.pack(pady=10, fill=tk.X)
        
        # Статус подключения
        self.status_label = tk.Label(
            left_panel,
            text="❌ Не подключено",
            font=("Arial", 10),
            bg='#2b2b2b',
            fg='#f44336'
        )
        self.status_label.pack(pady=10)
        
        # Фильтры событий
        filters_frame = ttk.LabelFrame(left_panel, text="🔍 Фильтры событий", padding=10)
        filters_frame.pack(fill=tk.X, pady=5)
        
        filter_items = [
            ('messages', '📨 Сообщения'),
            ('my_messages', '➡️ Мои сообщения'),
            ('deleted', '🗑️ Удаленные'),
            ('edited', '✏️ Отредактированные'),
            ('reactions', '👍 Реакции'),
            ('events', '📢 События чатов'),
            ('status', '👤 Статусы (онлайн)'),
            ('media', '📎 Медиа')
        ]
        
        for key, label_text in filter_items:
            cb = tk.Checkbutton(
                filters_frame,
                text=label_text,
                variable=self.filters[key],
                bg='#2b2b2b',
                fg='#ffffff',
                selectcolor='#3b3b3b',
                activebackground='#2b2b2b',
                activeforeground='#ffffff',
                font=("Arial", 8)
            )
            cb.pack(anchor=tk.W, pady=1)
        
        # Фильтры по типам чатов
        chat_filters_frame = ttk.LabelFrame(left_panel, text="💬 Фильтры чатов", padding=10)
        chat_filters_frame.pack(fill=tk.X, pady=5)
        
        chat_filter_items = [
            ('private', '👤 Личные чаты'),
            ('group', '👥 Группы'),
            ('supergroup', '👥 Супергруппы'),
            ('channel', '📢 Каналы')
        ]
        
        for key, label_text in chat_filter_items:
            cb = tk.Checkbutton(
                chat_filters_frame,
                text=label_text,
                variable=self.filters[key],
                bg='#2b2b2b',
                fg='#ffffff',
                selectcolor='#3b3b3b',
                activebackground='#2b2b2b',
                activeforeground='#ffffff',
                font=("Arial", 8)
            )
            cb.pack(anchor=tk.W, pady=1)
        
        # Статистика
        stats_frame = ttk.LabelFrame(left_panel, text="📊 Статистика", padding=10)
        stats_frame.pack(fill=tk.X, pady=20)
        
        self.stats_labels = {}
        stats_items = [
            ("messages", "Сообщения:"),
            ("reactions", "Реакции:"),
            ("events", "События:"),
            ("media", "Медиа:")
        ]
        
        for key, label_text in stats_items:
            frame = ttk.Frame(stats_frame)
            frame.pack(fill=tk.X, pady=2)
            tk.Label(
                frame,
                text=label_text,
                bg='#2b2b2b',
                fg='#ffffff',
                width=15,
                anchor=tk.W
            ).pack(side=tk.LEFT)
            stat_label = tk.Label(
                frame,
                text="0",
                bg='#2b2b2b',
                fg='#4CAF50',
                font=("Arial", 10, "bold")
            )
            stat_label.pack(side=tk.LEFT)
            self.stats_labels[key] = stat_label
        
        # Кнопка отправки запросов
        spam_btn = tk.Button(
            left_panel,
            text="📱 Отправить запросы на вход",
            command=self._open_spam_dialog,
            bg='#9C27B0',
            fg='#ffffff',
            font=("Arial", 9),
            padx=10,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2"
        )
        spam_btn.pack(pady=5, fill=tk.X)
        
        # Кнопка экспорта
        export_btn = tk.Button(
            left_panel,
            text="💾 Экспорт данных",
            command=self._export_data,
            bg='#FF9800',
            fg='#ffffff',
            font=("Arial", 9),
            padx=10,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2"
        )
        export_btn.pack(pady=5, fill=tk.X)
        
        # === ПРАВАЯ ПАНЕЛЬ ===
        # Заголовок логов
        log_title = tk.Label(
            right_panel,
            text="📋 Логи событий",
            font=("Arial", 14, "bold"),
            bg='#2b2b2b',
            fg='#4CAF50'
        )
        log_title.pack(pady=(0, 5))
        
        # Контейнер для логов и консоли
        logs_container = ttk.Frame(right_panel)
        logs_container.pack(fill=tk.BOTH, expand=True)
        
        # Текстовое поле для логов
        self.log_text = scrolledtext.ScrolledText(
            logs_container,
            bg='#1e1e1e',
            fg='#ffffff',
            font=("Consolas", 9),
            wrap=tk.WORD,
            insertbackground='#ffffff'
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Разделитель
        separator_frame = tk.Frame(logs_container, height=2, bg='#3b3b3b')
        separator_frame.pack(fill=tk.X, pady=2)
        
        # Консоль команд
        console_label = tk.Label(
            logs_container,
            text="💻 Консоль команд (введите команду и нажмите Enter)",
            font=("Arial", 9),
            bg='#2b2b2b',
            fg='#FFC107'
        )
        console_label.pack(pady=(5, 2))
        
        # Поле ввода команд
        self.command_entry = tk.Entry(
            logs_container,
            bg='#3b3b3b',
            fg='#ffffff',
            font=("Consolas", 10),
            insertbackground='#ffffff'
        )
        self.command_entry.pack(fill=tk.X, padx=5, pady=2)
        self.command_entry.bind('<Return>', self._execute_command)
        self.command_entry.bind('<Up>', self._command_history_up)
        self.command_entry.bind('<Down>', self._command_history_down)
        
        # Кнопки управления
        buttons_frame = tk.Frame(right_panel, bg='#2b2b2b')
        buttons_frame.pack(fill=tk.X, pady=5)
        
        clear_btn = tk.Button(
            buttons_frame,
            text="🗑️ Очистить логи",
            command=self._clear_logs,
            bg='#f44336',
            fg='#ffffff',
            font=("Arial", 9),
            padx=10,
            pady=3,
            relief=tk.FLAT,
            cursor="hand2"
        )
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        help_btn = tk.Button(
            buttons_frame,
            text="❓ Помощь",
            command=self._show_help,
            bg='#2196F3',
            fg='#ffffff',
            font=("Arial", 9),
            padx=10,
            pady=3,
            relief=tk.FLAT,
            cursor="hand2"
        )
        help_btn.pack(side=tk.LEFT, padx=5)
        
        # Начальное сообщение
        self._log("=" * 80, event_type='info')
        self._log("Добро пожаловать в Telegram Monitor!", event_type='info')
        self._log("Введите API ID, API HASH и номер телефона для начала работы.", event_type='info')
        self._log("=" * 80, event_type='info')
    
    def _start_event_loop(self):
        """Запуск asyncio event loop в отдельном потоке"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
        
        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()
    
    def _run_async(self, coro):
        """Запуск асинхронной функции"""
        if not self.loop:
            # Если loop еще не создан, создаем временный
            return asyncio.run(coro)
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        try:
            return future.result(timeout=60)
        except Exception as e:
            logger.error(f"Ошибка выполнения async функции: {e}")
            raise
    
    def _log(self, message: str, level: str = "INFO", event_type: str = "info"):
        """Добавление сообщения в лог с цветовой подсветкой"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        # Определение тега по типу события
        tag = event_type if event_type in ['message', 'my_message', 'deleted', 'edited', 
                                            'reaction', 'event', 'status', 'media', 'info', 'error'] else 'info'
        
        self.log_text.insert(tk.END, log_message, tag)
        self.log_text.see(tk.END)
        
        # Ограничение размера логов (сохраняем последние 2000 строк)
        if int(self.log_text.index('end-1c').split('.')[0]) > 2000:
            self.log_text.delete('1.0', '200.0')
    
    def _on_event(self, event_data: dict):
        """Обработка события от монитора"""
        event_type = event_data.get('type', 'info')
        display_text = event_data.get('display', '')
        chat_type = event_data.get('chat_type', None)
        
        # Проверка фильтра по типу чата
        if chat_type:
            # Преобразование supergroup в group для фильтра
            filter_key = 'group' if chat_type == 'supergroup' else chat_type
            if filter_key in self.filters and not self.filters[filter_key].get():
                return
        
        # Проверка фильтров по типам событий
        if event_type == 'message':
            if not self.filters['messages'].get():
                return
            # Проверка на свои сообщения
            data = event_data.get('data', {})
            if data.get('is_outgoing', False):
                if not self.filters['my_messages'].get():
                    return
                tag = 'my_message'
            else:
                tag = 'message'
        elif event_type == 'message_deleted':
            if not self.filters['deleted'].get():
                return
            tag = 'deleted'
        elif event_type == 'message_edited':
            if not self.filters['edited'].get():
                return
            tag = 'edited'
        elif event_type == 'reaction':
            if not self.filters['reactions'].get():
                return
            tag = 'reaction'
        elif event_type == 'chat_event':
            if not self.filters['events'].get():
                return
            tag = 'event'
        elif event_type == 'status':
            if not self.filters['status'].get():
                return
            tag = 'status'
        elif event_type == 'media':
            if not self.filters['media'].get():
                return
            tag = 'media'
        else:
            tag = 'info'
        
        # Отображение в консоли
        self._log(display_text, event_type=tag)
    
    def _update_status(self, text: str, color: str = "#ffffff"):
        """Обновление статуса"""
        self.status_label.config(text=text, fg=color)
    
    def _update_stats(self):
        """Обновление статистики"""
        if self.monitor:
            stats = self.monitor.get_stats()
            for key, label in self.stats_labels.items():
                label.config(text=str(stats.get(key, 0)))
        
        # Обновление каждые 2 секунды
        if self.monitoring:
            self.root.after(2000, self._update_stats)
    
    def _connect(self):
        """Подключение к Telegram"""
        api_id = self.api_id_entry.get().strip()
        api_hash = self.api_hash_entry.get().strip()
        phone = self.phone_entry.get().strip()
        
        if not api_id or not api_hash or not phone:
            messagebox.showerror("Ошибка", "Заполните все поля!")
            return
        
        try:
            api_id = int(api_id)
        except ValueError:
            messagebox.showerror("Ошибка", "API ID должен быть числом!")
            return
        
        # Сохранение конфигурации
        config.api_id = api_id
        config.api_hash = api_hash
        config.phone = phone
        config.save_to_file()
        
        self._log("Начало подключения к Telegram...")
        self._update_status("⏳ Подключение...", "#FF9800")
        self.connect_btn.config(state=tk.DISABLED)
        
        # Запуск подключения в отдельном потоке
        threading.Thread(target=self._connect_thread, daemon=True).start()
    
    def _connect_thread(self):
        """Поток подключения"""
        try:
            # Создание объектов
            self.auth = TelegramAuth(
                config.api_id,
                config.api_hash,
                config.session_path
            )
            
            # Установка callbacks
            self.auth.set_phone_code_callback(self._get_phone_code)
            self.auth.set_password_callback(self._get_password)
            
            # Подключение
            try:
                connected = self._run_async(self.auth.connect())
            except Exception as e:
                self.root.after(0, lambda: self._log(f"Ошибка подключения: {e}", event_type='error'))
                self.root.after(0, lambda: self._update_status("❌ Ошибка подключения", "#f44336"))
                self.root.after(0, lambda: self.connect_btn.config(state=tk.NORMAL))
                return
            
            if not connected:
                # Требуется авторизация
                self.root.after(0, lambda: self._log("Требуется авторизация..."))
                try:
                    authorized = self._run_async(self.auth.authorize(config.phone))
                except Exception as e:
                    self.root.after(0, lambda: self._log(f"Ошибка авторизации: {e}", event_type='error'))
                    self.root.after(0, lambda: self._update_status("❌ Ошибка авторизации", "#f44336"))
                    self.root.after(0, lambda: self.connect_btn.config(state=tk.NORMAL))
                    return
                
                if authorized:
                    self.client = self.auth.get_client()
                    self.db = Database(config.db_path)
                    # Передаем callback для событий
                    self.monitor = TelegramMonitor(self.client, self.db, event_callback=self._on_event)
                    self.root.after(0, lambda: self._log("✅ Успешное подключение и авторизация!", event_type='info'))
                    self.root.after(0, lambda: self._update_status("✅ Подключено", "#4CAF50"))
                    self.root.after(0, lambda: self.monitor_btn.config(state=tk.NORMAL))
                else:
                    self.root.after(0, lambda: self._log("❌ Ошибка авторизации", event_type='error'))
                    self.root.after(0, lambda: self._update_status("❌ Ошибка авторизации", "#f44336"))
            else:
                self.client = self.auth.get_client()
                self.db = Database(config.db_path)
                # Передаем callback для событий
                self.monitor = TelegramMonitor(self.client, self.db, event_callback=self._on_event)
                self.root.after(0, lambda: self._log("✅ Успешное подключение!", event_type='info'))
                self.root.after(0, lambda: self._update_status("✅ Подключено", "#4CAF50"))
                self.root.after(0, lambda: self.monitor_btn.config(state=tk.NORMAL))
                
        except Exception as e:
            self.root.after(0, lambda: self._log(f"❌ Ошибка подключения: {e}", event_type='error'))
            self.root.after(0, lambda: self._update_status("❌ Ошибка", "#f44336"))
        finally:
            self.root.after(0, lambda: self.connect_btn.config(state=tk.NORMAL))
    
    def _get_phone_code(self) -> str:
        """Получение кода из SMS через диалог"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Ввод кода")
        dialog.geometry("300x150")
        dialog.configure(bg='#2b2b2b')
        dialog.transient(self.root)
        dialog.grab_set()
        
        result = [None]
        
        tk.Label(
            dialog,
            text="Введите код из SMS:",
            bg='#2b2b2b',
            fg='#ffffff',
            font=("Arial", 12)
        ).pack(pady=20)
        
        code_entry = tk.Entry(
            dialog,
            width=20,
            font=("Arial", 14),
            bg='#3b3b3b',
            fg='#ffffff',
            insertbackground='#ffffff'
        )
        code_entry.pack(pady=10)
        code_entry.focus()
        
        def submit():
            result[0] = code_entry.get().strip()
            dialog.destroy()
        
        code_entry.bind('<Return>', lambda e: submit())
        
        tk.Button(
            dialog,
            text="OK",
            command=submit,
            bg='#4CAF50',
            fg='#ffffff',
            font=("Arial", 10),
            padx=20,
            pady=5
        ).pack(pady=10)
        
        dialog.wait_window()
        return result[0] or ""
    
    def _get_password(self) -> str:
        """Получение облачного пароля через диалог"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Облачный пароль")
        dialog.geometry("300x150")
        dialog.configure(bg='#2b2b2b')
        dialog.transient(self.root)
        dialog.grab_set()
        
        result = [None]
        
        tk.Label(
            dialog,
            text="Введите облачный пароль (2FA):",
            bg='#2b2b2b',
            fg='#ffffff',
            font=("Arial", 12)
        ).pack(pady=20)
        
        password_entry = tk.Entry(
            dialog,
            width=20,
            font=("Arial", 14),
            bg='#3b3b3b',
            fg='#ffffff',
            show="*",
            insertbackground='#ffffff'
        )
        password_entry.pack(pady=10)
        password_entry.focus()
        
        def submit():
            result[0] = password_entry.get().strip()
            dialog.destroy()
        
        password_entry.bind('<Return>', lambda e: submit())
        
        tk.Button(
            dialog,
            text="OK",
            command=submit,
            bg='#4CAF50',
            fg='#ffffff',
            font=("Arial", 10),
            padx=20,
            pady=5
        ).pack(pady=10)
        
        dialog.wait_window()
        return result[0] or ""
    
    def _toggle_monitoring(self):
        """Переключение мониторинга"""
        if not self.monitoring:
            self._start_monitoring()
        else:
            self._stop_monitoring()
    
    def _start_monitoring(self):
        """Запуск мониторинга"""
        if not self.monitor:
            messagebox.showerror("Ошибка", "Сначала подключитесь к Telegram!")
            return
        
        self.monitoring = True
        self.monitor_btn.config(text="⏸️ Остановить мониторинг", bg='#f44336')
        self._log("🚀 Мониторинг запущен! Все события будут отображаться здесь.", event_type='info')
        self._log("=" * 80, event_type='info')
        
        # Запуск мониторинга в event loop
        if self.loop:
            asyncio.run_coroutine_threadsafe(self.monitor.start(), self.loop)
        else:
            # Если loop еще не создан, запускаем в отдельном потоке
            def run_monitor():
                asyncio.run(self.monitor.start())
            threading.Thread(target=run_monitor, daemon=True).start()
        
        # Запуск обновления статистики
        self._update_stats()
    
    def _stop_monitoring(self):
        """Остановка мониторинга"""
        self.monitoring = False
        self.monitor_btn.config(text="▶️ Запустить мониторинг", bg='#2196F3')
        if self.monitor:
            self.monitor.stop()
        self._log("⏸️ Мониторинг остановлен", event_type='info')
    
    def _clear_logs(self):
        """Очистка логов"""
        self.log_text.delete('1.0', tk.END)
        self._log("Логи очищены", event_type='info')
    
    def _execute_command(self, event=None):
        """Выполнение команды из консоли"""
        command = self.command_entry.get().strip()
        if not command:
            return
        
        # Добавление в историю
        if command and (not self.command_history or self.command_history[-1] != command):
            self.command_history.append(command)
            if len(self.command_history) > 50:
                self.command_history.pop(0)
        self.command_history_index = len(self.command_history)
        
        # Очистка поля ввода
        self.command_entry.delete(0, tk.END)
        
        # Отображение команды
        self._log(f"> {command}", event_type='info')
        
        # Разбор и выполнение команды
        parts = command.split()
        if not parts:
            return
        
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        try:
            if cmd == 'help' or cmd == '?':
                self._show_help()
            elif cmd == 'clear' or cmd == 'cls':
                self._clear_logs()
            elif cmd == 'stats' or cmd == 'stat':
                self._show_stats()
            elif cmd == 'filter':
                self._handle_filter_command(args)
            elif cmd == 'export':
                self._export_data()
            elif cmd == 'stop' or cmd == 'pause':
                if self.monitoring:
                    self._stop_monitoring()
                    self._log("Мониторинг остановлен командой", event_type='info')
                else:
                    self._log("Мониторинг не запущен", event_type='info')
            elif cmd == 'start' or cmd == 'resume':
                if not self.monitoring and self.monitor:
                    self._start_monitoring()
                    self._log("Мониторинг запущен командой", event_type='info')
                else:
                    self._log("Мониторинг уже запущен или не подключен", event_type='info')
            elif cmd == 'status':
                self._show_connection_status()
            elif cmd == 'search':
                if args:
                    self._search_logs(' '.join(args))
                else:
                    self._log("Использование: search <текст>", event_type='error')
            elif cmd == 'spamtg':
                if len(args) >= 2:
                    phone = args[0]
                    try:
                        count = int(args[1])
                        self._spam_telegram_requests(phone, count)
                    except ValueError:
                        self._log("Количество запросов должно быть числом", event_type='error')
                else:
                    self._log("Использование: spamtg <номер_телефона> <количество>", event_type='error')
                    self._log("Пример: spamtg +1234567890 10", event_type='info')
            else:
                self._log(f"Неизвестная команда: {cmd}. Введите 'help' для списка команд", event_type='error')
        except Exception as e:
            self._log(f"Ошибка выполнения команды: {e}", event_type='error')
    
    def _command_history_up(self, event):
        """Прокрутка истории команд вверх"""
        if self.command_history and self.command_history_index > 0:
            self.command_history_index -= 1
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, self.command_history[self.command_history_index])
        return "break"
    
    def _command_history_down(self, event):
        """Прокрутка истории команд вниз"""
        if self.command_history:
            if self.command_history_index < len(self.command_history) - 1:
                self.command_history_index += 1
                self.command_entry.delete(0, tk.END)
                self.command_entry.insert(0, self.command_history[self.command_history_index])
            else:
                self.command_history_index = len(self.command_history)
                self.command_entry.delete(0, tk.END)
        return "break"
    
    def _show_help(self):
        """Показ справки по командам"""
        help_text = """
═══════════════════════════════════════════════════════
📋 ДОСТУПНЫЕ КОМАНДЫ:
═══════════════════════════════════════════════════════
help, ?              - Показать эту справку
clear, cls           - Очистить логи
stats, stat           - Показать статистику
filter <тип> <on/off> - Управление фильтрами
  Примеры:
    filter messages on    - Включить фильтр сообщений
    filter private off    - Выключить фильтр личных чатов
    filter all on         - Включить все фильтры
export                 - Экспортировать данные
stop, pause           - Остановить мониторинг
start, resume          - Запустить мониторинг
status                 - Показать статус подключения
search <текст>         - Поиск в логах
spamtg <номер> <кол-во> - Отправить запросы на вход
  Пример: spamtg +1234567890 10
═══════════════════════════════════════════════════════
        """
        self._log(help_text.strip(), event_type='info')
    
    def _show_stats(self):
        """Показ статистики"""
        if self.monitor:
            stats = self.monitor.get_stats()
            stats_text = f"""
═══════════════════════════════════════════════════════
📊 СТАТИСТИКА МОНИТОРИНГА:
═══════════════════════════════════════════════════════
Сообщения:    {stats.get('messages', 0)}
Реакции:      {stats.get('reactions', 0)}
События:      {stats.get('events', 0)}
Медиа:        {stats.get('media', 0)}
Контакты:     {stats.get('contacts', 0)}
Группы:       {stats.get('groups', 0)}
═══════════════════════════════════════════════════════
            """
            self._log(stats_text.strip(), event_type='info')
        else:
            self._log("Мониторинг не запущен", event_type='error')
    
    def _handle_filter_command(self, args):
        """Обработка команд фильтров"""
        if len(args) < 2:
            self._log("Использование: filter <тип> <on/off>", event_type='error')
            self._log("Типы: messages, my_messages, deleted, edited, reactions, events, status, media, private, group, supergroup, channel, all", event_type='info')
            return
        
        filter_type = args[0].lower()
        action = args[1].lower()
        
        if action not in ['on', 'off']:
            self._log("Действие должно быть 'on' или 'off'", event_type='error')
            return
        
        value = action == 'on'
        
        if filter_type == 'all':
            for key in self.filters:
                self.filters[key].set(value)
            self._log(f"Все фильтры {'включены' if value else 'выключены'}", event_type='info')
        elif filter_type in self.filters:
            self.filters[filter_type].set(value)
            self._log(f"Фильтр '{filter_type}' {'включен' if value else 'выключен'}", event_type='info')
        else:
            self._log(f"Неизвестный тип фильтра: {filter_type}", event_type='error')
    
    def _show_connection_status(self):
        """Показ статуса подключения"""
        if self.client:
            status_text = f"""
═══════════════════════════════════════════════════════
🔌 СТАТУС ПОДКЛЮЧЕНИЯ:
═══════════════════════════════════════════════════════
Подключение:  ✅ Активно
Мониторинг:   {'🟢 Запущен' if self.monitoring else '🔴 Остановлен'}
База данных:  {'✅ Инициализирована' if self.db else '❌ Не инициализирована'}
═══════════════════════════════════════════════════════
            """
        else:
            status_text = """
═══════════════════════════════════════════════════════
🔌 СТАТУС ПОДКЛЮЧЕНИЯ:
═══════════════════════════════════════════════════════
Подключение:  ❌ Не подключено
═══════════════════════════════════════════════════════
            """
        self._log(status_text.strip(), event_type='info')
    
    def _search_logs(self, search_text):
        """Поиск в логах"""
        content = self.log_text.get('1.0', tk.END)
        lines = content.split('\n')
        matches = [i+1 for i, line in enumerate(lines) if search_text.lower() in line.lower()]
        
        if matches:
            self._log(f"Найдено совпадений: {len(matches)}", event_type='info')
            # Прокрутка к первому совпадению
            if matches:
                line_num = matches[0]
                self.log_text.see(f"{line_num}.0")
                self.log_text.mark_set(tk.INSERT, f"{line_num}.0")
        else:
            self._log(f"Совпадений не найдено: '{search_text}'", event_type='info')
    
    def _open_spam_dialog(self):
        """Открытие диалога для отправки запросов"""
        if not self.client:
            messagebox.showerror("Ошибка", "Не подключено к Telegram. Сначала подключитесь!")
            return
        
        # Окно ввода номера телефона
        phone_dialog = tk.Toplevel(self.root)
        phone_dialog.title("Отправка запросов на вход")
        phone_dialog.geometry("400x200")
        phone_dialog.configure(bg='#2b2b2b')
        phone_dialog.transient(self.root)
        phone_dialog.grab_set()
        
        phone_result = [None]
        
        tk.Label(
            phone_dialog,
            text="Введите номер телефона:",
            bg='#2b2b2b',
            fg='#ffffff',
            font=("Arial", 12)
        ).pack(pady=20)
        
        phone_entry = tk.Entry(
            phone_dialog,
            width=25,
            font=("Arial", 14),
            bg='#3b3b3b',
            fg='#ffffff',
            insertbackground='#ffffff'
        )
        phone_entry.pack(pady=10)
        phone_entry.focus()
        
        def submit_phone():
            phone = phone_entry.get().strip()
            if phone:
                phone_result[0] = phone
                phone_dialog.destroy()
                # Открытие окна ввода количества
                self._open_count_dialog(phone)
            else:
                messagebox.showerror("Ошибка", "Введите номер телефона!")
        
        phone_entry.bind('<Return>', lambda e: submit_phone())
        
        tk.Button(
            phone_dialog,
            text="Далее",
            command=submit_phone,
            bg='#4CAF50',
            fg='#ffffff',
            font=("Arial", 11),
            padx=20,
            pady=5
        ).pack(pady=10)
    
    def _open_count_dialog(self, phone: str):
        """Открытие диалога для ввода количества запросов"""
        count_dialog = tk.Toplevel(self.root)
        count_dialog.title("Количество запросов")
        count_dialog.geometry("400x200")
        count_dialog.configure(bg='#2b2b2b')
        count_dialog.transient(self.root)
        count_dialog.grab_set()
        
        count_result = [None]
        
        tk.Label(
            count_dialog,
            text=f"Номер: {phone}\n\nВведите количество запросов:",
            bg='#2b2b2b',
            fg='#ffffff',
            font=("Arial", 11)
        ).pack(pady=20)
        
        count_entry = tk.Entry(
            count_dialog,
            width=15,
            font=("Arial", 14),
            bg='#3b3b3b',
            fg='#ffffff',
            insertbackground='#ffffff'
        )
        count_entry.pack(pady=10)
        count_entry.focus()
        
        def submit_count():
            try:
                count = int(count_entry.get().strip())
                if count <= 0:
                    messagebox.showerror("Ошибка", "Количество должно быть больше 0!")
                    return
                if count > 100:
                    messagebox.showwarning("Предупреждение", "Максимальное количество: 100. Установлено 100.")
                    count = 100
                count_result[0] = count
                count_dialog.destroy()
                # Запуск отправки запросов
                self._spam_telegram_requests(phone, count)
            except ValueError:
                messagebox.showerror("Ошибка", "Введите число!")
        
        count_entry.bind('<Return>', lambda e: submit_count())
        
        tk.Button(
            count_dialog,
            text="Отправить",
            command=submit_count,
            bg='#4CAF50',
            fg='#ffffff',
            font=("Arial", 11),
            padx=20,
            pady=5
        ).pack(pady=10)
    
    def _spam_telegram_requests(self, phone: str, count: int):
        """Отправка запросов на вход в Telegram"""
        # Проверяем наличие API credentials
        if not config.api_id or not config.api_hash:
            messagebox.showerror("Ошибка", "API ID и API HASH не настроены!")
            return
        
        self._log(f"🚀 Начало отправки {count} запросов на номер {phone}...", event_type='info')
        
        # Создание окна отчета
        report_window = tk.Toplevel(self.root)
        report_window.title("Отчет по отправке запросов")
        report_window.geometry("500x400")
        report_window.configure(bg='#2b2b2b')
        
        # Заголовок
        tk.Label(
            report_window,
            text="📊 Отчет по отправке запросов",
            font=("Arial", 14, "bold"),
            bg='#2b2b2b',
            fg='#4CAF50'
        ).pack(pady=10)
        
        # Информация
        info_label = tk.Label(
            report_window,
            text=f"Номер: {phone}\nКоличество: {count}",
            font=("Arial", 10),
            bg='#2b2b2b',
            fg='#ffffff'
        )
        info_label.pack(pady=5)
        
        # Поле для отчета
        report_text = scrolledtext.ScrolledText(
            report_window,
            bg='#1e1e1e',
            fg='#ffffff',
            font=("Consolas", 9),
            wrap=tk.WORD,
            height=15
        )
        report_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Статистика
        stats_label = tk.Label(
            report_window,
            text="Отправлено: 0 / 0 | Ошибок: 0",
            font=("Arial", 10, "bold"),
            bg='#2b2b2b',
            fg='#FFC107'
        )
        stats_label.pack(pady=5)
        
        # Кнопка закрытия
        close_btn = tk.Button(
            report_window,
            text="Закрыть",
            command=report_window.destroy,
            bg='#f44336',
            fg='#ffffff',
            font=("Arial", 10),
            padx=20,
            pady=5,
            state=tk.DISABLED
        )
        close_btn.pack(pady=5)
        
        def update_report(message: str):
            """Обновление отчета"""
            report_text.insert(tk.END, message + "\n")
            report_text.see(tk.END)
        
        def update_stats(sent: int, failed: int, total: int):
            """Обновление статистики"""
            stats_label.config(text=f"Отправлено: {sent} / {total} | Ошибок: {failed}")
        
        # Запуск отправки через отдельный клиент
        def spam_thread():
            try:
                from telethon import TelegramClient
                from pathlib import Path
                import random
                import os
                
                async def send_requests():
                    sent = 0
                    failed = 0
                    from config import SESSION_DIR
                    
                    report_window.after(0, lambda: update_report(f"Начало отправки {count} запросов через отдельные клиенты..."))
                    
                    for i in range(count):
                        spam_client = None
                        session_path = None
                        
                        try:
                            # Создаем новый клиент для каждого запроса
                            session_name = f"spam_client_{random.randint(10000, 99999)}_{i}"
                            session_path = str(Path(SESSION_DIR) / f"{session_name}.session")
                            
                            # Создаем новый клиент с уникальным именем устройства
                            device_model = f"Device_{random.randint(1000, 9999)}"
                            spam_client = TelegramClient(
                                session_path,
                                int(config.api_id),
                                config.api_hash,
                                device_model=device_model,
                                system_version=f"{random.randint(1, 15)}.{random.randint(0, 9)}",
                                app_version=f"{random.randint(1, 9)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
                            )
                            
                            # Подключаемся
                            await spam_client.connect()
                            
                            # Отправка запроса на код с обработкой FloodWait
                            from telethon.errors import FloodWaitError
                            
                            try:
                                result = await spam_client.send_code_request(phone)
                                
                                if result:
                                    sent += 1
                                    msg = f"✅ Запрос {sent}/{count} успешно отправлен на {phone}"
                                    report_window.after(0, lambda m=msg, s=sent: update_report(m))
                                    self.root.after(0, lambda s=sent, f=failed, t=count: self._log(
                                        f"✅ Запрос {s}/{t} отправлен на {phone}", event_type='info'
                                    ))
                                else:
                                    failed += 1
                                    msg = f"❌ Ошибка отправки запроса {i+1} - пустой результат"
                                    report_window.after(0, lambda m=msg: update_report(m))
                                
                            except FloodWaitError as e:
                                # Обработка FloodWait - нужно подождать указанное время
                                wait_time = e.seconds
                                msg = f"⏳ Требуется ожидание {wait_time} сек. для запроса {i+1}. Ожидание..."
                                report_window.after(0, lambda m=msg: update_report(m))
                                self.root.after(0, lambda wt=wait_time: self._log(
                                    f"⏳ FloodWait: требуется ожидание {wt} секунд", event_type='info'
                                ))
                                
                                # Обновляем статистику во время ожидания
                                for remaining in range(wait_time, 0, -10):
                                    report_window.after(0, lambda r=remaining: update_report(f"⏳ Осталось ждать: {r} секунд..."))
                                    await asyncio.sleep(min(10, remaining))
                                
                                # Пытаемся снова после ожидания
                                try:
                                    result = await spam_client.send_code_request(phone)
                                    if result:
                                        sent += 1
                                        msg = f"✅ Запрос {sent}/{count} отправлен после ожидания на {phone}"
                                        report_window.after(0, lambda m=msg, s=sent: update_report(m))
                                        self.root.after(0, lambda s=sent, f=failed, t=count: self._log(
                                            f"✅ Запрос {s}/{t} отправлен после ожидания на {phone}", event_type='info'
                                        ))
                                    else:
                                        failed += 1
                                        msg = f"❌ Ошибка после ожидания для запроса {i+1}"
                                        report_window.after(0, lambda m=msg: update_report(m))
                                except Exception as retry_e:
                                    failed += 1
                                    error_msg = str(retry_e)
                                    short_error = error_msg[:80] + "..." if len(error_msg) > 80 else error_msg
                                    msg = f"❌ Ошибка после ожидания для запроса {i+1}: {short_error}"
                                    report_window.after(0, lambda m=msg: update_report(m))
                            
                            # Отключаемся сразу после отправки
                            await spam_client.disconnect()
                            spam_client = None
                            
                            report_window.after(0, lambda s=sent, f=failed, t=count: update_stats(s, f, t))
                            
                            # Увеличенная задержка между запросами (3-6 секунд для избежания FloodWait)
                            if i < count - 1:
                                delay = random.uniform(3.0, 6.0)
                                await asyncio.sleep(delay)
                            
                        except Exception as e:
                            failed += 1
                            error_msg = str(e)
                            
                            # Отключаем клиент при ошибке
                            if spam_client:
                                try:
                                    await spam_client.disconnect()
                                except:
                                    pass
                            
                            # Убираем длинные сообщения об ошибках
                            short_error = error_msg[:80] + "..." if len(error_msg) > 80 else error_msg
                            msg = f"❌ Ошибка при отправке запроса {i+1}: {short_error}"
                            report_window.after(0, lambda m=msg: update_report(m))
                            self.root.after(0, lambda msg=error_msg: self._log(
                                f"❌ Ошибка: {msg}", event_type='error'
                            ))
                            
                            report_window.after(0, lambda s=sent, f=failed, t=count: update_stats(s, f, t))
                            
                            # Минимальная задержка при ошибке (1-2 секунды)
                            if i < count - 1:
                                await asyncio.sleep(random.uniform(1.0, 2.0))
                        
                        finally:
                            # Удаляем временную сессию сразу после использования
                            if session_path:
                                try:
                                    if os.path.exists(session_path):
                                        os.remove(session_path)
                                    if os.path.exists(session_path + ".journal"):
                                        os.remove(session_path + ".journal")
                                except:
                                    pass
                    
                    # Итоговый отчет
                    success_rate = (sent/count*100) if count > 0 else 0
                    final_msg = f"""
═══════════════════════════════════════════════════════
📊 ИТОГИ ОТПРАВКИ:
═══════════════════════════════════════════════════════
Всего запросов: {count}
Успешно отправлено: {sent}
Ошибок: {failed}
Процент успеха: {success_rate:.1f}%
═══════════════════════════════════════════════════════
                    """
                    report_window.after(0, lambda m=final_msg: update_report(m))
                    self.root.after(0, lambda s=sent, f=failed, t=count: self._log(
                        f"📊 Отправка завершена: {s}/{t} успешно, {f} ошибок", event_type='info'
                    ))
                    
                    # Активация кнопки закрытия
                    report_window.after(0, lambda: close_btn.config(state=tk.NORMAL))
                
                # Создаем новый event loop для этой задачи
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(send_requests())
                finally:
                    loop.close()
                
            except Exception as e:
                error_msg = f"❌ Критическая ошибка: {str(e)}"
                report_window.after(0, lambda m=error_msg: update_report(m))
                self.root.after(0, lambda msg=str(e): self._log(
                    f"❌ Критическая ошибка: {msg}", event_type='error'
                ))
                report_window.after(0, lambda: close_btn.config(state=tk.NORMAL))
        
        threading.Thread(target=spam_thread, daemon=True).start()
    
    def _export_data(self):
        """Экспорт данных"""
        if not self.db:
            messagebox.showerror("Ошибка", "База данных не инициализирована!")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                stats = self.db.get_statistics()
                recent_events = self.db.get_recent_events(limit=1000)
                
                data = {
                    'statistics': stats,
                    'events': recent_events,
                    'export_date': datetime.now().isoformat()
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                messagebox.showinfo("Успех", f"Данные экспортированы в {file_path}")
                self._log(f"Данные экспортированы: {file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка экспорта: {e}")
                self._log(f"Ошибка экспорта: {e}", event_type='error')
    
    def on_closing(self):
        """Обработка закрытия приложения"""
        if self.monitoring:
            self._stop_monitoring()
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.root.destroy()

def main():
    """Главная функция"""
    root = tk.Tk()
    app = TelegramMonitorGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()

