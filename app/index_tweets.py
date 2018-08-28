#!/usr/bin/env python
# -*- coding: utf-8 -*-
import gzip
import os
import json
from datetime import datetime
from config import ARCHIVE_BASEDIR, EXPORTS_BASEDIR
from app import models, db
from sqlalchemy.exc import IntegrityError

def indexUserSearch(id, dateStart, dateStop, RT):
    count = 0
    if not os.path.isdir(EXPORTS_BASEDIR):
        os.makedirs(EXPORTS_BASEDIR)
    q = models.TWITTER.query.filter(models.TWITTER.row_id == id).first()

    if dateStart == None:
        dateStart = datetime.min
    else:
        dateStart = datetime.combine(dateStart,datetime.min.time())

    if dateStop == None:
        dateStop = datetime.max
    else:
        dateStop = datetime.combine(dateStop, datetime.min.time())



    for filename in os.listdir(os.path.join(ARCHIVE_BASEDIR,q.title)):
        if filename.endswith(".gz"):
            for line in gzip.open(os.path.join(ARCHIVE_BASEDIR,q.title,filename)):

                tweet = json.loads(line.decode('utf-8'))
                try:
                    add = models.SEARCH(tweet["user"]["name"],
                                        tweet["user"]["screen_name"],
                                        tweet["id"],
                                        tweet["full_text"],
                                        datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y'),
                                        q.row_id,
                                        tweet['retweet_count'],
                                        '',
                                        'twitter',
                                        None,
                                        0,
                                        None)
                    tweetDate = datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y')


                    if tweetDate > dateStart and tweetDate < dateStop:
                        if RT:
                            if not 'retweeted_status' in tweet:
                                db.session.add(add)
                                count = count + 1
                                db.session.commit()
                        else:
                            db.session.add(add)
                            count = count + 1
                            db.session.commit()




                except IntegrityError:
                    db.session.rollback()

    db.session.close()


#indexUserSearch(1, RT=True, dateStart=datetime.strptime('2018-05-01','%Y-%m-%d'), dateStop=datetime.strptime('2018-08-01','%Y-%m-%d'))

#indexUserSearch(1, RT=False, dateStart=None, dateStop=None)



