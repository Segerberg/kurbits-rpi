import gzip
import os
import json
from datetime import datetime
from config import ARCHIVE_BASEDIR, EXPORTS_BASEDIR
from app import models, db
import uuid
from collections import Counter

"""
This is a modified script from the Twarc utils library
https://github.com/DocNow/twarc
"""

def topUsers(id):
    tags = []
    export_uuid = uuid.uuid4()
    if not os.path.isdir(EXPORTS_BASEDIR):
        os.makedirs(EXPORTS_BASEDIR)
    q = models.TWITTER.query.filter(models.TWITTER.row_id == id).first()
    with open(os.path.join(EXPORTS_BASEDIR, 'topusers_{}.txt'.format(export_uuid)), 'w+') as f:
        for filename in os.listdir(os.path.join(ARCHIVE_BASEDIR,q.targetType,q.title[0],q.title)):
            try:
                if filename.endswith(".gz"):
                    for line in gzip.open(os.path.join(ARCHIVE_BASEDIR,q.targetType,q.title[0],q.title,filename)):
                        tweet = json.loads(line.decode('utf-8'))
                        tags.append(tweet['user']['screen_name'])
            except:
                continue
        counts = Counter(tags)
        for t in counts.most_common(10):
            f.write(str(t))
            f.write('\n')

    addExportRef = models.EXPORTS(url='topusers_{}.txt'.format(export_uuid),type='Top Users',exported=datetime.now(),count=None)
    q.exports.append(addExportRef)
    db.session.commit()
    db.session.close()


def topUsersCollection(id):
    tags = []
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
    with open(os.path.join(EXPORTS_BASEDIR, 'topusers_{}.txt'.format(export_uuid)), 'w+') as f:
        for target in linkedTargets:
            print (target.title)
            try:
                for filename in os.listdir(os.path.join(ARCHIVE_BASEDIR,target.targetType,target.title[0],target.title)):

                        if filename.endswith(".gz"):
                            for line in gzip.open(os.path.join(ARCHIVE_BASEDIR,target.targetType,target.title[0],target.title,filename)):
                                tweet = json.loads(line.decode('utf-8'))
                                tweetDate = datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y')
                                if tweetDate > dbDateStart and tweetDate < dbDateStop:
                                    tags.append(tweet['user']['screen_name'])
            except:
                continue
        counts = Counter(tags)
        for t in counts.most_common(10):
            f.write(str(t))
            f.write('\n')

    addExportRef = models.EXPORTS(url='topusers_{}.txt'.format(export_uuid),type='Top Users',exported=datetime.now(),count=None)
    q.exports.append(addExportRef)
    db.session.commit()
    db.session.close()




