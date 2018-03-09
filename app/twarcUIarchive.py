#!/usr/bin/env python

"""
This is a modified version of twarc-archive script from the Twarc utils library

"""
from __future__ import print_function

import os
import re
import sys
import gzip
import json
import twarc
import logging
import argparse
from app import app, models, db, current_app
from datetime import datetime
from config import ARCHIVE_BASEDIR,CONSUMER_KEY,CONSUMER_SECRET,ACCESS_TOKEN,ACCESS_SECRET

archive_file_fmt = "tweets-%04i.json.gz"
archive_file_pat = "tweets-(\d+).json.gz$"


def twittercrawl(id):
    with app.app_context():
        TWITTER = models.TWITTER.query.filter(models.TWITTER.row_id == id).first()
        if not os.path.isdir(os.path.join(ARCHIVE_BASEDIR,TWITTER.title)):
            os.makedirs(os.path.join(ARCHIVE_BASEDIR,TWITTER.title))

        logging.basicConfig(
            filename=os.path.join(os.path.join(ARCHIVE_BASEDIR,TWITTER.title), "archive.log"),
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s"
        )

        logging.info("logging search for %s to %s", TWITTER.title, os.path.join(ARCHIVE_BASEDIR,TWITTER.title))

        t = twarc.Twarc(consumer_key=CONSUMER_KEY,
                        consumer_secret=CONSUMER_SECRET,
                        access_token=ACCESS_TOKEN,
                        access_token_secret=ACCESS_SECRET,
                        #config=args.config,
                        #tweet_mode=args.tweet_mode
                        )

        last_archive = get_last_archive(os.path.join(ARCHIVE_BASEDIR,TWITTER.title))
        if last_archive:
            last_id = json.loads(next(gzip.open(last_archive, 'rt')))['id_str']
        else:
            last_id = None

        if TWITTER.targetType == "Search":
            tweets = t.search(TWITTER.searchString, since_id=last_id)

        elif TWITTER.targetType == "User":
            #if re.match("^\d+$", TWITTER.title):
            #    tweets = t.timeline(userid=TWITTER.title, since_id=last_id)
            #else:
            tweets = t.timeline(screen_name=TWITTER.title, since_id=last_id)
        else:
            raise Exception("invalid twarc_command")

        next_archive = get_next_archive(os.path.join(ARCHIVE_BASEDIR,TWITTER.title))

        # we only create the file if there are new tweets to save
        # this prevents empty archive files
        fh = None
        tweetCount = 0

        for tweet in tweets:
            if not fh:
                fh = gzip.open(next_archive, "wt")
            #logging.info("archived %s", tweet["id_str"])
            fh.write(json.dumps(tweet))
            fh.write("\n")
            tweetCount = tweetCount + 1

            if TWITTER.index:

                add = models.SEARCH(tweet["user"]["name"],
                                    tweet["user"]["screen_name"],
                                    tweet["full_text"],
                                    datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y'),
                                    TWITTER.row_id,
                                    tweet['retweet_count'],
                                    '',
                                    'twitter')
                db.session.add(add)

        if fh:
            fh.close()

            # update database with new total tweet count
            TWITTER.totalTweets = TWITTER.totalTweets + tweetCount
            addLog = models.CRAWLLOG(tag_title=TWITTER.title, event_start=datetime.now(),
                                     event_text='archived {} tweets'.format(tweetCount))
            TWITTER.logs.append(addLog)
            db.session.commit()
        else:
            addLog = models.CRAWLLOG(tag_title=TWITTER.title, event_start=datetime.now(),
                                     event_text='archived {} tweets'.format(tweetCount))
            TWITTER.logs.append(addLog)

            db.session.commit()




def get_last_archive(archive_dir):
    count = 0
    for filename in os.listdir(archive_dir):
        m = re.match(archive_file_pat, filename)
        if m and int(m.group(1)) > count:
            count = int(m.group(1))
    if count != 0:
        return os.path.join(archive_dir, archive_file_fmt % count)
    else:
        return None

def get_next_archive(archive_dir):
    last_archive = get_last_archive(archive_dir)
    if last_archive:
        m = re.search(archive_file_pat, last_archive)
        count = int(m.group(1)) + 1
    else:
        count = 1
    return os.path.join(archive_dir, archive_file_fmt % count)


