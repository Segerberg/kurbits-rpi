from app import db, models
from .twarcUIarchive import twittercrawl
from datetime import datetime, timedelta
from redis import Redis
from rq import Queue

q = Queue(connection=Redis())

def startScheduleCollectionCrawl(id):
        collectionLastCrawl = models.COLLECTION.query.get(id)
        collectionLastCrawl.lastCrawl = datetime.now()
        collectionLastCrawl.nextRun = datetime.now() + timedelta(seconds=int(collectionLastCrawl.scheduleInterval))
        db.session.commit()
        linkedTargets = models.COLLECTION.query. \
            filter(models.COLLECTION.row_id == id). \
            first(). \
            tags
        for target in linkedTargets:
            if target.status == '1':
                last_crawl = models.TWITTER.query.get(target.row_id)
                last_crawl.lastCrawl = datetime.now()
                db.session.commit()
                q.enqueue(twittercrawl, target.row_id, timeout=86400)
        db.session.close()


