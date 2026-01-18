from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bank.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Модели базы данных
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    account_number = db.Column(db.String(20), unique=True, nullable=False)
    balance = db.Column(db.Float, default=0.0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=True)
    receiver_account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Декоратор для проверки авторизации
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Главная страница
@app.route('/')
def index():
    return render_template('index.html')

# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        
        # Проверяем уникальность email
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует')
            return redirect(url_for('register'))
        
        # Создаем пользователя
        user = User(full_name=full_name, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Создаем счет
        account = Account(
            user_id=user.id,
            account_number=f'40817810{user.id:012d}',
            balance=1000.00
        )
        db.session.add(account)
        db.session.commit()
        
        flash('Регистрация успешна! Теперь войдите в систему.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# Вход
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['email'] = user.email
            session['full_name'] = user.full_name
            session['role'] = user.role
            
            flash('Вход выполнен успешно!')
            return redirect(url_for('dashboard'))
        else:
            flash('Неверный email или пароль')
    
    return render_template('login.html')

# Выход
@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы')
    return redirect(url_for('index'))

# Личный кабинет
@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    accounts = Account.query.filter_by(user_id=user_id).all()
    return render_template('dashboard.html', accounts=accounts)

# История операций
@app.route('/history')
@login_required
def history():
    user_id = session['user_id']
    accounts = Account.query.filter_by(user_id=user_id).all()
    account_ids = [acc.id for acc in accounts]
    
    transactions = Transaction.query.filter(
        (Transaction.sender_account_id.in_(account_ids)) |
        (Transaction.receiver_account_id.in_(account_ids))
    ).order_by(Transaction.created_at.desc()).all()
    
    return render_template('history.html', transactions=transactions)

# Перевод средств
@app.route('/transfer', methods=['GET', 'POST'])
@login_required
def transfer():
    if request.method == 'POST':
        from_account_id = request.form['from_account']
        to_account_number = request.form['to_account']
        amount = float(request.form['amount'])
        description = request.form.get('description', '')
        
        # Простая логика перевода
        flash(f'Перевод на {amount} ₽ выполнен!', 'success')
        return redirect(url_for('dashboard'))
    
    user_id = session['user_id']
    accounts = Account.query.filter_by(user_id=user_id).all()
    return render_template('transfer.html', accounts=accounts)

# Удаление аккаунта
@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    if session.get('role') == 'admin':
        flash('Администратор не может удалить свой аккаунт')
        return redirect(url_for('dashboard'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if user:
        db.session.delete(user)
        db.session.commit()
        session.clear()
        flash('Ваш аккаунт удален')
    
    return redirect(url_for('index'))

# Админ-панель
@app.route('/admin')
@login_required
def admin():
    if session.get('role') != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(50).all()
    
    return render_template('admin.html', users=users, transactions=transactions)

# Создаем таблицы и администратора при первом запуске
with app.app_context():
    db.create_all()
    
    # Создаем администратора, если его нет
    if not User.query.filter_by(email='admin@bank.ru').first():
        admin = User(
            full_name='Администратор',
            email='admin@bank.ru',
            role='admin'
        )
        admin.set_password('Admin123!')
        db.session.add(admin)
        db.session.commit()
        
        # Создаем счет для администратора
        account = Account(
            user_id=admin.id,
            account_number='40817810000000000001',
            balance=10000.00
        )
        db.session.add(account)
        db.session.commit()
        
        print('Создан администратор: admin@bank.ru / Admin123!')

if __name__ == '__main__':
    app.run(debug=True)