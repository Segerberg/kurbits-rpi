import os
from app import app, models, db
from config import SQLALCHEMY_DATABASE_URI, EXPORTS_BASEDIR, PGUSER, PGPASSWORD, BACKUP_BASEDIR
import sqlalchemy
import subprocess
from subprocess import check_output
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import uuid
from datetime import datetime
suffixes = ['b', 'kb', 'mb', 'gb', 'tb', 'pb']
#import gzip
#import delegator

def humansize(nbytes):
    i = 0
    while nbytes >= 1024 and i < len(suffixes)-1:
        nbytes /= 1024.
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[i])

def deleteindextweets(id):
    models.SEARCH.query.filter(models.SEARCH.ia_uri == None).filter(models.SEARCH.source==id).delete()
    db.session.commit()


def delIndex():
    models.SEARCH.query.filter(models.SEARCH.ia_uri == None).delete()
    db.session.commit()
    engine = sqlalchemy.create_engine(SQLALCHEMY_DATABASE_URI)
    connection = engine.raw_connection()
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = connection.cursor()
    #cursor.execute('SET zero_damaged_pages = on')
    cursor.execute('VACUUM ANALYSE "SEARCH"')
    cursor.execute('REINDEX TABLE "SEARCH"')

def vac():
    engine = sqlalchemy.create_engine(SQLALCHEMY_DATABASE_URI)
    connection = engine.raw_connection()
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = connection.cursor()
    cursor.execute('VACUUM FULL')



def backup_db():
    export_uuid = uuid.uuid4()
    os.putenv('PGUSER', PGUSER)
    os.putenv('PGPASSWORD', PGPASSWORD)
    if not os.path.isdir(BACKUP_BASEDIR):
        os.makedirs(BACKUP_BASEDIR)

    subprocess.call(['/home/pi/twarcUI/db_backup.sh'])
