import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        port="5432", 
        database="bank_db",
        user="postgres",
        password="1234"
    )
    print("✅ Подключение к PostgreSQL успешно!")
    conn.close()
except Exception as e:
    print(f"❌ Ошибка подключения: {e}")
    print("Проверьте:")
    print("1. Запущен ли PostgreSQL?")
    print("2. Правильный ли пароль?")
    print("3. Существует ли база bank_db?")