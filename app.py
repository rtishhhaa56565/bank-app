from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text, or_
import re
from datetime import datetime, timedelta
import os
import random
import string

app = Flask(__name__)

# Импортируем конфигурацию
from config import config
app.config.from_object(config)

db = SQLAlchemy(app)

# ==================== МОДЕЛИ БАЗЫ ДАННЫХ ====================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    role = db.Column(db.String(20), default='client')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    accounts = db.relationship('Account', backref='owner', lazy=True, cascade='all, delete-orphan')
    sent_transactions = db.relationship('Transaction', foreign_keys='Transaction.sender_user_id', backref='sender', lazy=True)
    received_transactions = db.relationship('Transaction', foreign_keys='Transaction.receiver_user_id', backref='receiver', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'accounts_count': len(self.accounts)
        }

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    account_number = db.Column(db.String(20), unique=True, nullable=False)
    account_type = db.Column(db.String(30), default='current')
    balance = db.Column(db.Float, default=0.0, nullable=False)
    currency = db.Column(db.String(3), default='RUB')
    interest_rate = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    sent_transactions = db.relationship('Transaction', foreign_keys='Transaction.sender_account_id', backref='sender_account', lazy=True)
    received_transactions = db.relationship('Transaction', foreign_keys='Transaction.receiver_account_id', backref='receiver_account', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'account_number': self.account_number,
            'account_type': self.account_type,
            'balance': self.balance,
            'currency': self.currency,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'user_name': self.owner.full_name if self.owner else None
        }

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_type = db.Column(db.String(30), nullable=False)
    sender_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    receiver_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sender_account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=True)
    receiver_account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='RUB')
    description = db.Column(db.String(500))
    status = db.Column(db.String(20), default='completed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reference_number = db.Column(db.String(50), unique=True)
    
    def generate_reference(self):
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random_str = ''.join(random.choices(string.digits, k=6))
        return f'TR{timestamp}{random_str}'
    
    def to_dict(self):
        return {
            'id': self.id,
            'transaction_type': self.transaction_type,
            'amount': self.amount,
            'currency': self.currency,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'reference_number': self.reference_number
        }

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def generate_account_number(user_id, account_type='current'):
    """Генерация номера счета (ровно 20 символов)"""
    prefix = {
        'current': '40817',
        'savings': '42301',
        'credit': '45201'
    }.get(account_type, '40817')
    
    # Формат: префикс (5) + 810 + user_id (10 цифр) = 18 символов
    # Добавим 2 случайные цифры для уникальности = 20 символов
    user_part = f"{user_id:010d}"  # 10 цифр с ведущими нулями
    random_part = ''.join(random.choices('0123456789', k=2))
    
    return f'{prefix}810{user_part}{random_part}'  # 5 + 3 + 10 + 2 = 20 символов

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
    if len(full_name.strip()) > 100:
        return ["Слишком длинное ФИО (максимум 100 символов)"]
    return []

def validate_phone(phone):
    if not phone:
        return []  # Телефон не обязателен
    
    # Более гибкая валидация телефона
    patterns = [
        r'^\+7\s?\(\d{3}\)\s?\d{3}-\d{2}-\d{2}$',  # +7 (999) 123-45-67
        r'^\+7\d{10}$',  # +79991234567
        r'^8\s?\(\d{3}\)\s?\d{3}-\d{2}-\d{2}$',  # 8 (999) 123-45-67
        r'^8\d{10}$',  # 89991234567
    ]
    
    for pattern in patterns:
        if re.match(pattern, phone):
            return []
    
    return ["Некорректный формат телефона. Примеры: +7 (999) 123-45-67, 89991234567"]

# ==================== ИНИЦИАЛИЗАЦИЯ БАЗЫ ====================
def init_database():
    with app.app_context():
        try:
            print("🔧 Создание таблиц...")
            db.create_all()
            print("✅ Таблицы созданы")
            
            # Проверяем и обновляем существующие номера счетов если они слишком длинные
            accounts = Account.query.all()
            for account in accounts:
                if len(account.account_number) != 20:
                    # Генерируем новый правильный номер счета
                    new_number = generate_account_number(account.user_id, account.account_type)
                    print(f"⚠️ Исправляю номер счета: {account.account_number} -> {new_number}")
                    account.account_number = new_number
            
            if accounts:
                db.session.commit()
                print("✅ Номера счетов проверены и исправлены")
            
            admin = User.query.filter_by(email='admin@bank.ru').first()
            if not admin:
                admin = User(
                    full_name='Администратор Банка',
                    email='admin@bank.ru',
                    role='admin',
                    phone='+7 (999) 123-45-67',
                    address='Москва, ул. Банковская, д. 1'
                )
                admin.set_password('Admin123!')
                db.session.add(admin)
                print("✅ Администратор создан")
            
            test_users = [
                {
                    'full_name': 'Тестовый Пользователь',
                    'email': 'user@test.ru',
                    'password': 'User123!',
                    'role': 'client',
                    'phone': '+7 (999) 111-22-33',
                    'address': 'Москва, ул. Тестовая, д. 10'
                },
                {
                    'full_name': 'Иванов Иван Иванович',
                    'email': 'ivanov@example.ru',
                    'password': 'Ivanov123!',
                    'role': 'client',
                    'phone': '+7 (999) 222-33-44',
                    'address': 'Санкт-Петербург, Невский пр., д. 25'
                },
                {
                    'full_name': 'Петрова Мария Сергеевна',
                    'email': 'petrova@example.ru',
                    'password': 'Petrova123!',
                    'role': 'client',
                    'phone': '+7 (999) 333-44-55',
                    'address': 'Екатеринбург, ул. Ленина, д. 50'
                }
            ]
            
            for user_data in test_users:
                existing_user = User.query.filter_by(email=user_data['email']).first()
                if not existing_user:
                    new_user = User(
                        full_name=user_data['full_name'],
                        email=user_data['email'],
                        role=user_data['role'],
                        phone=user_data['phone'],
                        address=user_data['address']
                    )
                    new_user.set_password(user_data['password'])
                    db.session.add(new_user)
                    print(f"✅ Создан пользователь: {user_data['email']}")
            
            db.session.commit()
            
            users = User.query.all()
            for user in users:
                existing_accounts = Account.query.filter_by(user_id=user.id).first()
                if not existing_accounts:
                    # Используем исправленную функцию генерации
                    account_number = generate_account_number(user.id, 'current')
                    
                    # Проверяем длину
                    if len(account_number) != 20:
                        print(f"⚠️ Предупреждение: номер счета {account_number} не 20 символов ({len(account_number)} символов)")
                        # Дополняем или обрезаем до 20 символов
                        if len(account_number) < 20:
                            account_number = account_number.ljust(20, '0')
                        else:
                            account_number = account_number[:20]
                    
                    current_account = Account(
                        user_id=user.id,
                        account_number=account_number,
                        account_type='current',
                        balance=100000.00 if user.role == 'admin' else random.uniform(5000, 50000),
                        status='active'
                    )
                    db.session.add(current_account)
                    
                    if user.role == 'client' and random.random() > 0.3:
                        savings_account_number = generate_account_number(user.id, 'savings')
                        if len(savings_account_number) != 20:
                            if len(savings_account_number) < 20:
                                savings_account_number = savings_account_number.ljust(20, '0')
                            else:
                                savings_account_number = savings_account_number[:20]
                        
                        savings_account = Account(
                            user_id=user.id,
                            account_number=savings_account_number,
                            account_type='savings',
                            balance=random.uniform(10000, 100000),
                            interest_rate=random.uniform(3.5, 7.0),
                            status='active'
                        )
                        db.session.add(savings_account)
                    
                    print(f"✅ Счета созданы для пользователя: {user.email}")
            
            db.session.commit()
            
            print("🔧 Создание тестовых транзакций...")
            accounts = Account.query.all()
            
            if accounts and len(accounts) >= 2:
                for i in range(5):
                    sender = random.choice(accounts)
                    receiver = random.choice([acc for acc in accounts if acc.id != sender.id])
                    
                    amount = random.uniform(100, 5000)
                    
                    transaction = Transaction(
                        transaction_type='transfer',
                        sender_user_id=sender.user_id,
                        receiver_user_id=receiver.user_id,
                        sender_account_id=sender.id,
                        receiver_account_id=receiver.id,
                        amount=amount,
                        description=f'Тестовая транзакция #{i+1}',
                        status='completed'
                    )
                    transaction.reference_number = transaction.generate_reference()
                    db.session.add(transaction)
                
                db.session.commit()
                print("✅ Тестовые транзакции созданы")
            
            print("=" * 60)
            print("🎉 БАЗА ДАННЫХ POSTGRESQL УСПЕШНО ИНИЦИАЛИЗИРОВАНА!")
            print("=" * 60)
            print("\n👥 СОЗДАНЫ ПОЛЬЗОВАТЕЛИ:")
            users = User.query.all()
            for user in users:
                role_icon = '👑' if user.role == 'admin' else '👤'
                print(f"   {role_icon} {user.full_name} ({user.email})")
                accounts = Account.query.filter_by(user_id=user.id).all()
                for acc in accounts:
                    print(f"      Счет: {acc.account_number} ({len(acc.account_number)} символов) - {acc.balance:.2f} {acc.currency}")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ Ошибка при инициализации базы данных: {e}")
            import traceback
            traceback.print_exc()
            try:
                db.session.rollback()
            except:
                pass

# ==================== ИСПРАВЛЕННЫЙ МАРШРУТ РЕГИСТРАЦИИ ====================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect('/dashboard')
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        errors = []
        
        # Валидация ФИО
        name_errors = validate_full_name(full_name)
        if name_errors:
            errors.extend(name_errors)
        elif not full_name:
            errors.append('Введите ФИО')
        
        # Валидация email
        if not email:
            errors.append('Введите email')
        elif not validate_email(email):
            errors.append('Некорректный email')
        else:
            # Проверяем существование пользователя
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                errors.append('Пользователь с таким email уже существует')
        
        # Валидация пароля
        if not password:
            errors.append('Введите пароль')
        else:
            pass_errors = validate_password(password)
            if pass_errors:
                errors.extend(pass_errors)
        
        # Проверка подтверждения пароля
        if not confirm_password:
            errors.append('Подтвердите пароль')
        elif password != confirm_password:
            errors.append('Пароли не совпадают')
        
        # Валидация телефона (не обязателен)
        if phone:
            phone_errors = validate_phone(phone)
            if phone_errors:
                errors.extend(phone_errors)
        
        # Если есть ошибки - показываем их
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html', 
                                 full_name=full_name, 
                                 email=email, 
                                 phone=phone)
        else:
            try:
                # Создаем нового пользователя
                new_user = User(
                    full_name=full_name,
                    email=email,
                    phone=phone if phone else None,
                    role='client'
                )
                new_user.set_password(password)
                
                db.session.add(new_user)
                db.session.commit()
                
                # Генерируем номер счета
                account_number = generate_account_number(new_user.id, 'current')
                
                # Убеждаемся, что номер счета ровно 20 символов
                if len(account_number) != 20:
                    if len(account_number) < 20:
                        account_number = account_number.ljust(20, '0')
                    else:
                        account_number = account_number[:20]
                
                # Создаем счет
                new_account = Account(
                    user_id=new_user.id,
                    account_number=account_number,
                    account_type='current',
                    balance=10000.00
                )
                db.session.add(new_account)
                db.session.commit()
                
                flash(f'Регистрация успешна! Ваш номер счета: {account_number}', 'success')
                flash('Теперь вы можете войти в систему', 'info')
                return redirect('/login')
                
            except Exception as e:
                db.session.rollback()
                error_msg = str(e)
                print(f"Ошибка при регистрации: {error_msg}")
                
                # Более понятные сообщения об ошибках
                if 'unique constraint' in error_msg.lower() and 'email' in error_msg.lower():
                    flash('Пользователь с таким email уже существует', 'danger')
                elif 'unique constraint' in error_msg.lower() and 'account_number' in error_msg.lower():
                    flash('Ошибка генерации номера счета. Попробуйте еще раз.', 'danger')
                else:
                    flash(f'Ошибка при регистрации: {error_msg}', 'danger')
                
                return render_template('register.html', 
                                     full_name=full_name, 
                                     email=email, 
                                     phone=phone)
    
    # GET запрос - просто показываем форму
    return render_template('register.html')

# ==================== МАРШРУТ ЛОГИНА ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect('/dashboard')
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        # Базовая валидация
        if not email:
            flash('Введите email', 'danger')
            return render_template('login.html')
        
        if not password:
            flash('Введите пароль', 'danger')
            return render_template('login.html')
        
        try:
            user = User.query.filter_by(email=email).first()
            
            if user and user.check_password(password):
                if not user.is_active:
                    flash('Ваш аккаунт заблокирован', 'danger')
                    return render_template('login.html')
                
                session['user_id'] = user.id
                session['email'] = user.email
                session['full_name'] = user.full_name
                session['role'] = user.role
                
                user.update_last_login()
                
                flash(f'Добро пожаловать, {user.full_name}!', 'success')
                return redirect('/dashboard')
            else:
                flash('Неверный email или пароль', 'danger')
                return render_template('login.html', email=email)
                
        except Exception as e:
            flash('Ошибка при входе в систему', 'danger')
            return render_template('login.html', email=email)
    
    return render_template('login.html')

# ==================== ИСПРАВЛЕННЫЙ МАРШРУТ ИСТОРИИ ====================

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect('/login')
    
    user = User.query.get(session['user_id'])
    user_account_ids = [acc.id for acc in Account.query.filter_by(user_id=user.id).all()]
    
    transactions = Transaction.query.filter(
        (Transaction.sender_account_id.in_(user_account_ids)) |
        (Transaction.receiver_account_id.in_(user_account_ids))
    ).order_by(Transaction.created_at.desc()).all()
    
    total_transactions = len(transactions)
    outgoing = sum(1 for t in transactions if t.sender_account_id in user_account_ids)
    incoming = total_transactions - outgoing
    
    # Рассчитываем общую сумму
    total_amount = 0
    for trans in transactions:
        total_amount += trans.amount
    
    transactions_list = []
    for trans in transactions:
        is_sender = trans.sender_account_id in user_account_ids
        sender_account = Account.query.get(trans.sender_account_id) if trans.sender_account_id else None
        receiver_account = Account.query.get(trans.receiver_account_id)
        
        transactions_list.append({
            'date': trans.created_at.strftime('%d.%m.%Y %H:%M:%S'),
            'type': 'outgoing' if is_sender else 'incoming',
            'from_account': sender_account.account_number if sender_account else 'Пополнение',
            'to_account': receiver_account.account_number,
            'amount': trans.amount,
            'description': trans.description,
            'status': trans.status,
            'reference': trans.reference_number
        })
    
    total_balance = sum(acc.balance for acc in Account.query.filter_by(user_id=user.id))
    
    return render_template('history.html',
                         transactions=transactions_list,
                         stats={
                             'total': total_transactions,
                             'outgoing': outgoing,
                             'incoming': incoming,
                             'total_amount': total_amount
                         },
                         total_balance=total_balance)

# ==================== ОСТАЛЬНЫЕ МАРШРУТЫ ====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Войдите в систему', 'warning')
        return redirect('/login')
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        flash('Пользователь не найден', 'danger')
        return redirect('/login')
    
    accounts = Account.query.filter_by(user_id=user.id, status='active').all()
    user_account_ids = [acc.id for acc in accounts]
    
    transactions = Transaction.query.filter(
        (Transaction.sender_account_id.in_(user_account_ids)) |
        (Transaction.receiver_account_id.in_(user_account_ids))
    ).order_by(Transaction.created_at.desc()).limit(5).all()
    
    accounts_list = [acc.to_dict() for acc in accounts]
    
    transactions_list = []
    for trans in transactions:
        is_sender = trans.sender_account_id in user_account_ids
        transactions_list.append({
            'date': trans.created_at.strftime('%d.%m.%Y %H:%M'),
            'description': trans.description or 'Без описания',
            'amount': -trans.amount if is_sender else trans.amount,
            'type': 'outgoing' if is_sender else 'incoming',
            'reference': trans.reference_number
        })
    
    total_balance = sum(acc.balance for acc in accounts)
    
    return render_template('dashboard.html',
                         user=session,
                         accounts=accounts_list,
                         transactions=transactions_list,
                         total_balance=total_balance)

@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    if 'user_id' not in session:
        return redirect('/login')
    
    user = User.query.get(session['user_id'])
    accounts = Account.query.filter_by(user_id=user.id, status='active').all()
    
    if request.method == 'POST':
        from_account_id = request.form.get('from_account')
        to_account_number = request.form.get('to_account', '').strip()
        amount = request.form.get('amount', '0')
        description = request.form.get('description', '').strip()
        
        errors = []
        
        try:
            amount_float = float(amount)
            if amount_float <= 0:
                errors.append('Сумма должна быть больше 0')
            elif amount_float > 1000000:
                errors.append('Максимальная сумма перевода: 1,000,000 ₽')
        except:
            errors.append('Некорректная сумма')
        
        if not from_account_id:
            errors.append('Выберите счет списания')
        else:
            from_account = Account.query.get(from_account_id)
            if not from_account:
                errors.append('Выбранный счет не существует')
            elif from_account.user_id != user.id:
                errors.append('Это не ваш счет')
            elif from_account.balance < amount_float:
                errors.append('Недостаточно средств на счете')
        
        if not to_account_number or len(to_account_number) != 20 or not to_account_number.isdigit():
            errors.append('Некорректный номер счета (ровно 20 цифр)')
        else:
            to_account = Account.query.filter_by(account_number=to_account_number).first()
            if not to_account:
                errors.append('Счет получателя не найден')
            elif to_account.status != 'active':
                errors.append('Счет получателя заблокирован')
            elif to_account.id == from_account_id:
                errors.append('Нельзя переводить на тот же счет')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
        else:
            try:
                from_account = Account.query.get(from_account_id)
                to_account = Account.query.filter_by(account_number=to_account_number).first()
                
                transaction = Transaction(
                    transaction_type='transfer',
                    sender_user_id=user.id,
                    receiver_user_id=to_account.user_id,
                    sender_account_id=from_account.id,
                    receiver_account_id=to_account.id,
                    amount=amount_float,
                    description=description or f'Перевод со счета {from_account.account_number}',
                    status='completed'
                )
                transaction.reference_number = transaction.generate_reference()
                
                from_account.balance -= amount_float
                to_account.balance += amount_float
                
                db.session.add(transaction)
                db.session.commit()
                
                flash(f'Перевод на сумму {amount_float:.2f} ₽ выполнен успешно!', 'success')
                flash(f'Номер транзакции: {transaction.reference_number}', 'info')
                return redirect('/dashboard')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при выполнении перевода: {str(e)}', 'danger')
    
    accounts_list = [acc.to_dict() for acc in accounts]
    
    # Получаем всех пользователей для подсказок
    all_users = []
    try:
        all_users_with_accounts = User.query.filter(
            User.id != user.id,
            User.is_active == True
        ).all()
        
        all_users = []
        for u in all_users_with_accounts:
            user_dict = u.to_dict()
            user_dict['accounts'] = Account.query.filter_by(user_id=u.id).all()
            all_users.append(user_dict)
            
    except Exception as e:
        print(f"Ошибка при получении пользователей: {e}")
    
    return render_template('transfer.html', 
                         accounts=accounts_list,
                         all_users=all_users[:10])

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect('/login')
    
    user = User.query.get(session['user_id'])
    accounts = Account.query.filter_by(user_id=user.id).all()
    
    user_data = user.to_dict()
    user_data['phone'] = user.phone
    user_data['address'] = user.address
    user_data['last_login'] = user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Никогда'
    user_data['accounts'] = [acc.to_dict() for acc in accounts]
    
    return render_template('profile.html', user=user_data)

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect('/login')
    
    user = User.query.get(session['user_id'])
    
    if user.role == 'admin':
        flash('Администратор не может удалить свой аккаунт', 'danger')
    else:
        try:
            user.is_active = False
            db.session.commit()
            
            session.clear()
            flash('Ваш аккаунт успешно удален', 'success')
            return redirect('/')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при удалении аккаунта: {str(e)}', 'danger')
    
    return redirect('/profile')

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
    
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_accounts = Account.query.count()
    active_accounts = Account.query.filter_by(status='active').count()
    total_transactions = Transaction.query.count()
    
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    recent_transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all()
    
    total_balance = db.session.query(db.func.sum(Account.balance)).scalar() or 0
    
    return render_template('admin.html',
                         total_users=total_users,
                         active_users=active_users,
                         total_accounts=total_accounts,
                         active_accounts=active_accounts,
                         total_transactions=total_transactions,
                         total_balance=total_balance,
                         recent_users=recent_users,
                         recent_transactions=recent_transactions)

@app.route('/admin_panel')
def admin_panel():
    return redirect(url_for('admin'))

@app.route('/admin/users')
def admin_users():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@app.route('/admin/transactions')
def admin_transactions():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(100).all()
    return jsonify([trans.to_dict() for trans in transactions])

@app.route('/api/users')
def api_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@app.route('/api/accounts')
def api_accounts():
    accounts = Account.query.all()
    return jsonify([acc.to_dict() for acc in accounts])

@app.route('/api/transactions')
def api_transactions():
    transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(100).all()
    return jsonify([trans.to_dict() for trans in transactions])

@app.route('/api/search_accounts', methods=['GET'])
def search_accounts():
    """API для поиска счетов по номеру или имени владельца"""
    if 'user_id' not in session:
        return jsonify({'error': 'Войдите в систему'}), 401
    
    current_user_id = session['user_id']
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify({'accounts': []})
    
    try:
        accounts = Account.query.join(User).filter(
            Account.user_id != current_user_id,
            Account.status == 'active',
            or_(
                Account.account_number.ilike(f'%{query}%'),
                User.full_name.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%')
            )
        ).limit(10).all()

        accounts_list = []
        for acc in accounts:
            accounts_list.append({
                'account_number': acc.account_number,
                'owner_name': acc.owner.full_name if acc.owner else 'Неизвестно',
                'balance': acc.balance,
                'account_type': acc.account_type
            })
        
        return jsonify({'accounts': accounts_list})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================

if __name__ == '__main__':
    # Инициализация базы данных
    init_database()
    
    # Запуск Flask приложения
    print("\n🌐 Запуск банковского приложения...")
    print("📌 Адрес: http://localhost:5000")
    print("📌 Админ: http://localhost:5000/admin")
    print("📌 Логин админа: admin@bank.ru / Admin123!")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)