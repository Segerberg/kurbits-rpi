from csv import writer
import gzip
import os
import json
from datetime import datetime
from config import ARCHIVE_BASEDIR, EXPORTS_BASEDIR
from app import models, db
import uuid


def csvUserSearch(id):
    count = 0
    export_uuid = uuid.uuid4()
    if not os.path.isdir(EXPORTS_BASEDIR):
        os.makedirs(EXPORTS_BASEDIR)
    q = models.TWITTER.query.filter(models.TWITTER.row_id == id).first()
    with open(os.path.join(EXPORTS_BASEDIR, 'csv_{}.csv'.format(export_uuid)), 'w+') as out_file:
        csv = writer(out_file)
        row = ('tweet_id',
               'tweet_created_at',
               'tweet_text',
               'lang',
               'screen_name',
               'name',
               'user_id',
               'verified',
               'user_created_at',
               'statues_count',
               'followers_count',
               'friends_count',
               'time_zone'
               )
        values = [value for value in row]
        csv.writerow(values)

        for filename in os.listdir(os.path.join(ARCHIVE_BASEDIR, q.title)):
            if filename.endswith(".gz"):
                for line in gzip.open(os.path.join(ARCHIVE_BASEDIR, q.title, filename)):
                    count = count + 1
                    tweet = json.loads(line.decode('utf-8'))
                    row = (
                        tweet['id'],
                        tweet['created_at'],
                        tweet['full_text'],
                        tweet['lang'],
                        tweet['user']['screen_name'],
                        tweet['user']['name'],
                        tweet['user']['id_str'],
                        tweet['user']['verified'],
                        tweet['user']['created_at'],
                        tweet['user']['statuses_count'],
                        tweet['user']['followers_count'],
                        tweet['user']['friends_count'],
                        tweet['user']['time_zone']

                    )
                    values = [value for value in row]
                    csv.writerow(values)
    addExportRef = models.EXPORTS(url='csv_{}.csv'.format(export_uuid), type='CSV',
                                  exported=datetime.now(), count=count)
    q.exports.append(addExportRef)
    db.session.commit()
    db.session.close()

def csvCollection(id):
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
    with open(os.path.join(EXPORTS_BASEDIR, 'csv_{}.csv'.format(export_uuid)), 'w+') as out_file:
        csv = writer(out_file)
        row = ('tweet_id',
               'tweet_created_at',
               'tweet_text',
               'lang',
               'screen_name',
               'name',
               'user_id',
               'verified',
               'user_created_at',
               'statues_count',
               'followers_count',
               'friends_count',
               'time_zone'
               )
        values = [value for value in row]
        csv.writerow(values)
        for target in linkedTargets:
            for filename in os.listdir(os.path.join(ARCHIVE_BASEDIR,target.title)):
                if filename.endswith(".gz"):
                    for line in gzip.open(os.path.join(ARCHIVE_BASEDIR,target.title,filename)):
                        tweet = json.loads(line.decode('utf-8'))
                        tweetDate = datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y')
                        if tweetDate > dbDateStart and tweetDate < dbDateStop:
                            count = count + 1
                            row = (
                                tweet['id'],
                                tweet['created_at'],
                                tweet['full_text'],
                                tweet['lang'],
                                tweet['user']['screen_name'],
                                tweet['user']['name'],
                                tweet['user']['id_str'],
                                tweet['user']['verified'],
                                tweet['user']['created_at'],
                                tweet['user']['statuses_count'],
                                tweet['user']['followers_count'],
                                tweet['user']['friends_count'],
                                tweet['user']['time_zone']

                            )
                            values = [value for value in row]
                            csv.writerow(values)

    addExportRef = models.EXPORTS(url='csv_{}.csv'.format(export_uuid), type='CSV',
                                  exported=datetime.now(), count=count)
    q.exports.append(addExportRef)
    db.session.commit()
    db.session.close()