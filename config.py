import os
basedir = os.path.abspath(os.path.dirname(__file__))
WTF_CSRF_ENABLED = True
SECRET_KEY = 'very-very-hard-to-guess'
#SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app3.db')
SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/kurbits2'
SQLALCHEMY_MIGRATE_REPO = os.path.join(basedir, 'db_repository')
SQLALCHEMY_TRACK_MODIFICATIONS = True
#WARCPROX_LISTNING_PORT = 9002
POSTS_PER_PAGE = 90
TARGETS_PER_PAGE = 500
ARCHIVE_BASEDIR = os.path.join(basedir, 'jobs')
EXPORTS_BASEDIR = os.path.join(basedir, 'exports')
TEMP_BASEDIR = os.path.join(basedir, 'temp')
CONSUMER_KEY = ''
CONSUMER_SECRET = ''
ACCESS_TOKEN = ''
ACCESS_SECRET = ''
REDIS_DB = os.path.join(basedir, 'redis.rdb')
MAP_VIEW = '57.70, 12.022'
MAP_ZOOM = '4'


