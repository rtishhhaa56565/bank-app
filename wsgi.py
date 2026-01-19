import sys
import os

# Добавляем путь к проекту
path = '/home/ваш_username/bank-app'  # Измените на ваш путь
if path not in sys.path:
    sys.path.append(path)

# Импортируем приложение
from app import app as application