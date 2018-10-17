import bagit
import shutil
import os
import zipfile
from app import models
from config import ARCHIVE_BASEDIR, EXPORTS_BASEDIR
import os, shutil
from app import models, db
from datetime import datetime

def make_archive(source, destination):
        base = os.path.basename(destination)
        name = base.split('.')[0]
        format = base.split('.')[1]
        archive_from = os.path.dirname(source)
        archive_to = os.path.basename(source.strip(os.sep))
        shutil.make_archive(name, format, archive_from, archive_to)
        shutil.move('%s.%s'%(name,format), destination)


def bagger(id):
    q = models.TWITTER.query.filter(models.TWITTER.row_id == id).first()
    dest = os.path.join(EXPORTS_BASEDIR,q.title)
    shutil.copytree(os.path.join(ARCHIVE_BASEDIR,q.targetType,q.title[0],q.title), dest)
    bag = bagit.make_bag(dest, {'target-type':q.targetType,
                                'title': q.title,
                                'search-string':q.searchString,
                                'search-language':q.searchLang,
                                'description':q.description,
                                'keywords':q.subject})
    make_archive(dest,os.path.join(EXPORTS_BASEDIR,'{}.zip'.format(q.title)))
    shutil.rmtree(dest)
    addExportRef = models.EXPORTS(url='{}.zip'.format(q.title), type='Bag', exported=datetime.now(),count=None)
    q.exports.append(addExportRef)
    db.session.commit()
    db.session.close()
