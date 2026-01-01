"""
Главный файл запуска приложения
"""
import sys
import os
from pathlib import Path

# Добавление текущей директории в путь
sys.path.insert(0, str(Path(__file__).parent))

from gui import main

if __name__ == "__main__":
    main()

