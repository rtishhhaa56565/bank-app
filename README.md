# Банк "Веб-Финанс" - РГЗ по WEB-программированию

## Описание
Веб-приложение для имитации банковских операций. Проект выполнен как расчетно-графическое задание.

**Студент:** Арышева А.Ю.  
**Группа:** ФБИ-34  
**Вариант:** 35 "Банк"

## Функционал
- Регистрация и авторизация пользователей
- Личный кабинет с отображением счетов
- Денежные переводы между счетами
- История операций
- Админ-панель для управления
- Удаление аккаунта
- Валидация всех входных данных

## Технологии
- **Backend:** Python 3.14 + Flask
- **Frontend:** HTML5, CSS3, JavaScript + Bootstrap 5
- **Database:** SQLite + SQLAlchemy
- **Authentication:** Session-based + Password hashing

## Установка
```bash
# 1. Клонировать репозиторий
git clone https://github.com/rtishhhaa56565/bank-app.git
cd bank-app

# 2. Создать виртуальное окружение
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux/Mac:
# source venv/bin/activate

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Запустить приложение
python app.py