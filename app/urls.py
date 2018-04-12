#!/usr/bin/env python
import gzip
import os
import json
from datetime import datetime
from config import ARCHIVE_BASEDIR, EXPORTS_BASEDIR
from app import models, db
import uuid
"""
This is a modified script from the Twarc utils library
https://github.com/DocNow/twarc
"""
def urlsUserSearch(id):
    count = 0
    export_uuid = uuid.uuid4()
    if not os.path.isdir(EXPORTS_BASEDIR):
        os.makedirs(EXPORTS_BASEDIR)
    q = models.TWITTER.query.filter(models.TWITTER.row_id == id).first()
    with open(os.path.join(EXPORTS_BASEDIR, 'urls_{}.txt'.format(export_uuid)), 'w+') as f:
        for filename in os.listdir(os.path.join(ARCHIVE_BASEDIR,q.title)):
            if filename.endswith(".gz"):
                for line in gzip.open(os.path.join(ARCHIVE_BASEDIR,q.title,filename)):
                    count = count + 1
                    tweet = json.loads(line.decode('utf-8'))
                    for url in tweet["entities"]["urls"]:
                        if 'unshortened_url' in url:
                            f.write(url['unshortened_url'])
                            f.write('\n')
                        elif url.get('expanded_url'):
                            f.write(url['expanded_url'])
                            f.write('\n')
                        elif url.get('url'):
                            f.write(url['url'])
                            f.write('\n')


    addExportRef = models.EXPORTS(url='urls_{}.txt'.format(export_uuid),type='Urls',exported=datetime.now(),count=count)
    q.exports.append(addExportRef)
    db.session.commit()
    db.session.close()

def urlsCollection(id):
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
    with open(os.path.join(EXPORTS_BASEDIR,'urls_{}.txt'.format(export_uuid)),'w+') as f:
        for target in linkedTargets:
            print (target.title)
            for filename in os.listdir(os.path.join(ARCHIVE_BASEDIR,target.title)):
                if filename.endswith(".gz"):
                    for line in gzip.open(os.path.join(ARCHIVE_BASEDIR,target.title,filename)):


                        tweet = json.loads(line.decode('utf-8'))
                        tweetDate = datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y')

                        if tweetDate > dbDateStart and tweetDate < dbDateStop:
                            for url in tweet["entities"]["urls"]:
                                if 'unshortened_url' in url:
                                    count = count + 1
                                    f.write(url['unshortened_url'])
                                    f.write('\n')
                                elif url.get('expanded_url'):
                                    count = count + 1
                                    f.write(url['expanded_url'])
                                    f.write('\n')
                                elif url.get('url'):
                                    count = count + 1
                                    f.write(url['url'])
                                    f.write('\n')


    addExportRef = models.EXPORTS(url='urls_{}.txt'.format(export_uuid),
                                  type='Urls', exported=datetime.now(), count=count)
    q.exports.append(addExportRef)
    db.session.commit()
    db.session.close()


