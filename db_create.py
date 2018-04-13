#!flask/bin/python
import os.path
from config import SQLALCHEMY_DATABASE_URI
from config import SQLALCHEMY_MIGRATE_REPO
from werkzeug.security import generate_password_hash

from app import db, models
from migrate.versioning import api
from migrate.exceptions import *

try:
    db.create_all()
    if not os.path.exists(SQLALCHEMY_MIGRATE_REPO):
        api.create(SQLALCHEMY_MIGRATE_REPO, 'database repository')
        api.version_control(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
    else:
        api.version_control(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO, api.version(SQLALCHEMY_MIGRATE_REPO))
except DatabaseAlreadyControlledError:
    print("Database %s already has version control" % SQLALCHEMY_DATABASE_URI)

print("Adding initial db values")
admin = models.USERS(user='admin', passw=generate_password_hash('admin'))
db.session.add(admin)
db.session.commit()
db.session.close()