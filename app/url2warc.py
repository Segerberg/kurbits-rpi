#!/usr/bin/env python
import os
import gzip
import json
import time
import queue
import hashlib
import logging
import sqlite3
import requests
import threading
from app import models, db
from config import ARCHIVE_BASEDIR
from datetime import timedelta
from warcio.warcwriter import WARCWriter
from warcio.statusandheaders import StatusAndHeaders

q = queue.Queue()
out_queue = queue.Queue()
BLOCK_SIZE = 25600


class GetResource(threading.Thread):

    def __init__(self, q, file):
        threading.Thread.__init__(self)
        self.q = q
        self.rlock = threading.Lock()
        self.out_queue = out_queue
        self.d = Dedup(file)

    def run(self):
        while True:
            host = self.q.get()

            try:
                r = requests.get(host, headers={'Accept-Encoding': 'identity'}, stream=True)
                data = [r.raw.headers.items(), r.raw, host, r.status_code, r.reason]
                print(data[2])
                self.out_queue.put(data)
                self.q.task_done()

            except requests.exceptions.RequestException as e:
                logging.error('%s for %s', e, data[2])
                print(e)
                self.q.task_done()
                continue


class WriteWarc(threading.Thread):

    def __init__(self, out_queue, warcfile,file):
        threading.Thread.__init__(self)
        self.out_queue = out_queue
        self.lock = threading.Lock()
        self.warcfile = warcfile
        self.dedup = Dedup(file)

    def run(self):

        with open(self.warcfile, 'ab') as output:
            while True:
                self.lock.acquire()
                data = self.out_queue.get()
                writer = WARCWriter(output, gzip=True)
                headers_list = data[0]
                http_headers = StatusAndHeaders('{} {}'.format(data[3], data[4]), headers_list, protocol='HTTP/1.0')
                record = writer.create_warc_record(data[2], 'response', payload=data[1], http_headers=http_headers)
                h = hashlib.sha1()
                h.update(record.raw_stream.read(BLOCK_SIZE))
                if self.dedup.lookup(h.hexdigest()):
                    record = writer.create_warc_record(data[2], 'revisit',
                                                       http_headers=http_headers)
                    writer.write_record(record)
                    self.out_queue.task_done()
                    self.lock.release()
                else:
                    self.dedup.save(h.hexdigest(), data[2])
                    record.raw_stream.seek(0)
                    writer.write_record(record)
                    self.out_queue.task_done()
                    self.lock.release()

class Dedup():
    """
    Stolen from warcprox
    https://github.com/internetarchive/warcprox/blob/master/warcprox/dedup.py
    """
    def __init__(self, file):
        self.file = file

    def start(self):
        conn = sqlite3.connect(self.file)
        conn.execute(
            'create table if not exists dedup ('
            '  key varchar(300) primary key,'
            '  value varchar(4000)'
            ');')
        conn.commit()
        conn.close()

    def save(self, digest_key, url):
        conn = sqlite3.connect(self.file)
        conn.execute(
            'insert or replace into dedup (key, value) values (?, ?)',
            (digest_key, url))
        conn.commit()
        conn.close()

    def lookup(self, digest_key, url=None):
        result = False
        conn = sqlite3.connect(self.file)
        cursor = conn.execute('select value from dedup where key = ?', (digest_key,))
        result_tuple = cursor.fetchone()
        conn.close()
        if result_tuple:
            result = True

        return result



def url2warc(id, filename):
    obj = models.TWITTER.query.filter(models.TWITTER.row_id == id).first()
    archive_dir = os.path.join(ARCHIVE_BASEDIR, obj.title)
    tweet_file = os.path.join(ARCHIVE_BASEDIR, obj.title,filename)
    start = time.time()
    if not os.path.isdir(archive_dir):
        os.mkdir(archive_dir)

    logging.basicConfig(
        filename=os.path.join(archive_dir, "url_harvest.log"),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    logging.getLogger(__name__)
    logging.info("Logging url harvest for %s", tweet_file)

    urls = []
    d = Dedup(os.path.join(archive_dir,'dedup.db'))
    d.start()
    uniqueUrlCount = 0
    duplicateUrlCount = 0

    if tweet_file.endswith('.gz'):
        tweetfile = gzip.open(tweet_file, 'r')
    else:
        tweetfile = open(tweet_file, 'r')

    logging.info("Checking for duplicate urls")

    for line in tweetfile:
        tweet = json.loads(line)
        try:
            for url in tweet["entities"]["urls"]:
                if 'unshortened_url' in url:
                    if not url['unshortened_url'] in urls:
                        urls.append(url['unshortened_url'])
                        q.put(url['unshortened_url'])
                        uniqueUrlCount += 1
                    else:
                        duplicateUrlCount += 1

                elif url.get('expanded_url'):
                    if not url['expanded_url'] in urls:
                        urls.append(url['expanded_url'])
                        q.put(url['expanded_url'])
                        uniqueUrlCount += 1
                    else:
                        duplicateUrlCount += 1

                elif url.get('url'):
                    if not url['url'] in urls:
                        urls.append(url['url'])
                        q.put(url['url'])
                        uniqueUrlCount += 1
                    else:
                        duplicateUrlCount += 1

        except:
            continue

    logging.info("Found %s total urls %s unique and %s duplicates", uniqueUrlCount+duplicateUrlCount, uniqueUrlCount, duplicateUrlCount)

    threads = int(3)



    for i in range(threads):
        t = GetResource(q,os.path.join(archive_dir,'dedup.db'))
        t.setDaemon(True)
        t.start()

    wt = WriteWarc(out_queue, os.path.join(archive_dir, '{}.urls.warc.gz'.format(filename.replace('.json.gz',''))),os.path.join(archive_dir,'dedup.db'))
    wt.setDaemon(True)
    wt.start()

    q.join()
    out_queue.join()
    logging.info("Finished url harvest in %s", str(timedelta(seconds=(time.time() - start))))

