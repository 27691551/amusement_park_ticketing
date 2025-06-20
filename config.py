import os

class Config(object):
    '''共用的設定，提供繼承之用，減少重複的配置'''
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_default_secret_key'
    TESTING = False
    DEBUG = False

class ProductionConfig(Config):
    DB_SERVER = '192.168.19.32'
    DATABASE_URI = 'mysql://user@localhost/foo'

class DevelopmentConfig(Config):
    DB_SERVER = 'localhost'
    DATABASE_URI = "sqlite:////tmp/foo.db"
    DEBUG = True

class TestingConfig(Config):
    DB_SERVER = 'localhost'
    DATABASE_URI = 'sqlite:///:memory:'
    TESTING = True