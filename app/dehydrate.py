import gzip
import os
import json
from datetime import datetime
from config import ARCHIVE_BASEDIR, EXPORTS_BASEDIR
from app import models, db
import uuid

def dehydrateUserSearch(id):
    count = 0
    export_uuid = uuid.uuid4()
    if not os.path.isdir(EXPORTS_BASEDIR):
        os.makedirs(EXPORTS_BASEDIR)
    q = models.TWITTER.query.filter(models.TWITTER.row_id == id).first()
    with open(os.path.join(EXPORTS_BASEDIR, '{}_dehydrate_UUID_{}.txt'.format(q.title, export_uuid)), 'w+') as f:
        for filename in os.listdir(os.path.join(ARCHIVE_BASEDIR,q.title)):
            if filename.endswith(".gz"):
                for line in gzip.open(os.path.join(ARCHIVE_BASEDIR,q.title,filename)):
                    count = count + 1
                    tweet = json.loads(line.decode('utf-8'))['id_str']
                    f.write(tweet)
                    f.write('\n')
    addExportRef = models.EXPORTS(url='{}_dehydrate_UUID_{}.txt'.format(q.title, export_uuid),type='Dehydrate',exported=datetime.now(),count=count)
    q.exports.append(addExportRef)
    db.session.commit()
    db.session.close()

def dehydrateCollection(id):
    count = 0
    export_uuid = uuid.uuid4()
    if not os.path.isdir(EXPORTS_BASEDIR):
        os.makedirs(EXPORTS_BASEDIR)
    q = models.COLLECTION.query.filter(models.COLLECTION.row_id == id).first()
    linkedTargets = models.COLLECTION.query. \
        filter(models.COLLECTION.row_id == id). \
        first(). \
        tags
    dbDateStart = q.inclDateStart
    dbDateStop = q.inclDateEnd
    with open(os.path.join(EXPORTS_BASEDIR,'{}_dehydrate_UUID_{}.txt'.format(q.title,export_uuid)),'w+') as f:
        for target in linkedTargets:
            print (target.title)
            for filename in os.listdir(os.path.join(ARCHIVE_BASEDIR,target.title)):
                if filename.endswith(".gz"):
                    for line in gzip.open(os.path.join(ARCHIVE_BASEDIR,target.title,filename)):

                        count = count + 1
                        tweet = json.loads(line.decode('utf-8'))
                        tweetDate = datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y')

                        if tweetDate > dbDateStart and tweetDate < dbDateStop:
                            f.write(tweet['id_str'])
                            f.write('\n')


    addExportRef = models.EXPORTS(url='{}_dehydrate_UUID_{}.txt'.format(q.title, export_uuid),
                                  type='Dehydrate', exported=datetime.now(), count=count)
    q.exports.append(addExportRef)
    db.session.commit()
    db.session.close()





