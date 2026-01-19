import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'bank-app-secret-key-2025'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:1234@localhost:5432/bank_app'
    
class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://ваш_username:ваш_пароль@ваш_хост/имя_базы'