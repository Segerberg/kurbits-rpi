import os
from app import app, models, db
from config import SQLALCHEMY_DATABASE_URI
import sqlalchemy
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
suffixes = ['b', 'kb', 'mb', 'gb', 'tb', 'pb']
def humansize(nbytes):
    i = 0
    while nbytes >= 1024 and i < len(suffixes)-1:
        nbytes /= 1024.
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[i])


def reboot():
    with app.app_context():
        os.system('reboot now')

def delIndex():
    models.SEARCH.query.filter(models.SEARCH.ia_uri == None).delete()
    db.session.commit()
    engine = sqlalchemy.create_engine(SQLALCHEMY_DATABASE_URI)
    connection = engine.raw_connection()
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = connection.cursor()
    cursor.execute('VACUUM ANALYSE "SEARCH"')

def vac():
    engine = sqlalchemy.create_engine(SQLALCHEMY_DATABASE_URI)
    connection = engine.raw_connection()
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = connection.cursor()
    cursor.execute('VACUUM FULL')
