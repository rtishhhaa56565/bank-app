from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import re
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bank-app-secret-key-2025'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bank.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==================== МОДЕЛИ БАЗЫ ДАННЫХ ====================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='client')  # client, admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    accounts = db.relationship('Account', backref='owner', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    account_number = db.Column(db.String(20), unique=True, nullable=False)
    balance = db.Column(db.Float, default=10000.0, nullable=False)
    currency = db.Column(db.String(3), default='RUB')
    status = db.Column(db.String(20), default='active')  # active, blocked
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_account_id = db.Column(db.Integer, nullable=True)
    receiver_account_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== ИНИЦИАЛИЗАЦИЯ БАЗЫ ====================
def init_database():
    """Инициализация базы данных"""
    # Удаляем старую базу если есть
    if os.path.exists('bank.db'):
        os.remove('bank.db')
        print("🗑️ Старая база данных удалена")
    
    # Создаем таблицы
    db.create_all()
    print("✅ Таблицы созданы")
    
    # Создаем администратора
    try:
        admin = User(
            full_name='Администратор Банка',
            email='admin@bank.ru',
            role='admin'
        )
        admin.set_password('Admin123!')
        db.session.add(admin)
        db.session.commit()
        print("✅ Администратор создан")
        
        # Счет для администратора
        admin_account = Account(
            user_id=admin.id,
            account_number='40817810000000000001',
            balance=50000.00
        )
        db.session.add(admin_account)
    except Exception as e:
        db.session.rollback()
        print(f"⚠️ Администратор уже существует: {e}")
    
    # Создаем тестового пользователя
    try:
        client = User(
            full_name='Тестовый Пользователь',
            email='user@test.ru',
            role='client'
        )
        client.set_password('User123!')
        db.session.add(client)
        db.session.commit()
        print("✅ Тестовый пользователь создан")
        
        # Счет для пользователя
        client_account = Account(
            user_id=client.id,
            account_number='40817810000000000002',
            balance=20000.00
        )
        db.session.add(client_account)
    except Exception as e:
        db.session.rollback()
        print(f"⚠️ Тестовый пользователь уже существует: {e}")
    
    db.session.commit()
    print("=" * 50)
    print("🎉 БАЗА ДАННЫХ ГОТОВА")
    print("=" * 50)
    print("Тестовые пользователи:")
    print("👑 Администратор: admin@bank.ru / Admin123!")
    print("👤 Пользователь: user@test.ru / User123!")
    print("=" * 50)

# ==================== ВАЛИДАЦИЯ ====================
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_password(password):
    errors = []
    if len(password) < 8:
        errors.append("Минимум 8 символов")
    if not re.search(r'[A-Z]', password):
        errors.append("Хотя бы одна заглавная буква")
    if not re.search(r'[a-z]', password):
        errors.append("Хотя бы одна строчная буква")
    if not re.search(r'\d', password):
        errors.append("Хотя бы одна цифра")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Хотя бы один спецсимвол")
    if re.search(r'[а-яА-Я]', password):
        errors.append("Только латинские буквы")
    return errors

def validate_full_name(full_name):
    if not full_name or len(full_name.strip()) < 2:
        return ["Минимум 2 символа"]
    if re.search(r'\d', full_name):
        return ["Не должно содержать цифры"]
    return []

# ==================== МАРШРУТЫ ====================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect('/dashboard')
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        # Проверка администратора
        if email == 'admin@bank.ru' and password == 'Admin123!':
            session['user_id'] = 999
            session['email'] = email
            session['full_name'] = 'Администратор'
            session['role'] = 'admin'
            flash('Вход выполнен как администратор', 'success')
            return redirect('/dashboard')
        
        # Проверка тестового пользователя
        if email == 'user@test.ru' and password == 'User123!':
            session['user_id'] = 1
            session['email'] = email
            session['full_name'] = 'Тестовый Пользователь'
            session['role'] = 'client'
            flash('Вход выполнен успешно', 'success')
            return redirect('/dashboard')
        
        flash('Неверный email или пароль', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect('/dashboard')
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        errors = []
        
        # Валидация
        errors.extend(validate_full_name(full_name))
        
        if not email:
            errors.append('Введите email')
        elif not validate_email(email):
            errors.append('Некорректный email')
        
        pass_errors = validate_password(password)
        errors.extend(pass_errors)
        
        if password != confirm_password:
            errors.append('Пароли не совпадают')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
        else:
            flash(f'Регистрация успешна (демо): {full_name}', 'success')
            return redirect('/login')
    
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Войдите в систему', 'warning')
        return redirect('/login')
    
    # Тестовые данные
    accounts = [
        {'account_number': '40817810000000000001', 'balance': 15000.50},
        {'account_number': '40817810000000000002', 'balance': 5000.00}
    ] if session.get('user_id') == 1 else [
        {'account_number': '40817810999999999999', 'balance': 100000.00}
    ]
    
    transactions = [
        {'date': '18.01.2026 10:30', 'description': 'Перевод клиенту', 'amount': -5000.00},
        {'date': '17.01.2026 14:20', 'description': 'Пополнение счета', 'amount': 2000.00},
        {'date': '16.01.2026 09:15', 'description': 'Оплата услуг', 'amount': -1500.00}
    ]
    
    total_balance = sum(acc['balance'] for acc in accounts)
    
    return render_template('dashboard.html',
                         user=session,
                         accounts=accounts,
                         transactions=transactions,
                         total_balance=total_balance)

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect('/login')
    
    # Тестовые данные
    transactions = [
        {
            'date': '18.01.2026 10:30:15',
            'type': 'outgoing',
            'from_account': '40817810000000000001',
            'to_account': '40702810100000000001',
            'amount': 5000.00,
            'description': 'Подарок на день рождения',
            'status': 'completed'
        },
        {
            'date': '18.01.2026 09:15:22',
            'type': 'outgoing',
            'from_account': '40817810000000000001',
            'to_account': '40702810100000000002',
            'amount': 5000.00,
            'description': 'Оплата услуг',
            'status': 'completed'
        },
        {
            'date': '17.01.2026 16:45:10',
            'type': 'incoming',
            'from_account': None,
            'to_account': '40817810000000000001',
            'amount': 2000.00,
            'description': 'Пополнение счета',
            'status': 'completed'
        }
    ]
    
    stats = {
        'total': len(transactions),
        'outgoing': sum(1 for t in transactions if t['type'] == 'outgoing'),
        'incoming': sum(1 for t in transactions if t['type'] == 'incoming'),
        'total_amount': sum(t['amount'] for t in transactions)
    }
    
    return render_template('history.html',
                         transactions=transactions,
                         stats=stats,
                         total_balance=20000.00)

@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    if 'user_id' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        from_account = request.form.get('from_account')
        to_account = request.form.get('to_account', '').strip()
        amount = request.form.get('amount', '0')
        description = request.form.get('description', '').strip()
        
        errors = []
        
        try:
            amount_float = float(amount)
            if amount_float <= 0:
                errors.append('Сумма должна быть больше 0')
        except:
            errors.append('Некорректная сумма')
        
        if not to_account or len(to_account) != 20 or not to_account.isdigit():
            errors.append('Некорректный номер счета (20 цифр)')
        
        if not from_account:
            errors.append('Выберите счет списания')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
        else:
            flash(f'Перевод на {amount} ₽ выполнен успешно!', 'success')
            return redirect('/dashboard')
    
    accounts = [
        {'id': '1', 'account_number': '40817810000000000001', 'balance': 15000.50},
        {'id': '2', 'account_number': '40817810000000000002', 'balance': 5000.00}
    ]
    
    return render_template('transfer.html', accounts=accounts)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_data = {
        'email': session.get('email', ''),
        'full_name': session.get('full_name', ''),
        'role': session.get('role', 'client'),
        'created_at': '2025-01-15 10:30:00'
    }
    
    return render_template('profile.html', user=user_data)

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect('/login')
    
    if session.get('role') == 'admin':
        flash('Администратор не может удалить свой аккаунт', 'danger')
    else:
        session.clear()
        flash('Ваш аккаунт успешно удален', 'success')
    
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect('/')

@app.route('/admin')
def admin():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Доступ запрещен', 'danger')
        return redirect('/dashboard')
    
    users = [
        {'id': 1, 'email': 'admin@bank.ru', 'full_name': 'Администратор', 'role': 'admin', 'created_at': '2025-01-01'},
        {'id': 2, 'email': 'user@test.ru', 'full_name': 'Тестовый Пользователь', 'role': 'client', 'created_at': '2025-01-15'},
        {'id': 3, 'email': 'client1@example.ru', 'full_name': 'Иванов Иван', 'role': 'client', 'created_at': '2025-01-20'}
    ]
    
    transactions = [
        {'id': 1, 'from': '40817810000000000001', 'to': '40702810100000000001', 'amount': 5000.00, 'date': '2025-01-18 10:30:15'},
        {'id': 2, 'from': '40817810000000000001', 'to': '40702810100000000002', 'amount': 5000.00, 'date': '2025-01-18 09:15:22'},
        {'id': 3, 'from': None, 'to': '40817810000000000002', 'amount': 20000.00, 'date': '2025-01-17 14:20:00'}
    ]
    
    return render_template('admin.html', users=users, transactions=transactions)

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    with app.app_context():
        init_database()
    
    print("\n🚀 Сервер запускается...")
    print("🌐 Откройте в браузере: http://localhost:5000")
    print("\n👥 Тестовые пользователи:")
    print("   👑 Администратор: admin@bank.ru / Admin123!")
    print("   👤 Пользователь: user@test.ru / User123!")
    print("\n" + "="*50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)