import os
from datetime import datetime
from config import EXPORTS_BASEDIR,CONSUMER_KEY,CONSUMER_SECRET,ACCESS_TOKEN,ACCESS_SECRET
from app import models, db, app
import uuid
import twarc

def Followers(id):
    with app.test_request_context():
        t = twarc.Twarc(consumer_key=CONSUMER_KEY,
                    consumer_secret=CONSUMER_SECRET,
                    access_token=ACCESS_TOKEN,
                    access_token_secret=ACCESS_SECRET)
        count = 0
        export_uuid = uuid.uuid4()
        if not os.path.isdir(EXPORTS_BASEDIR):
            os.makedirs(EXPORTS_BASEDIR)
        q = models.TWITTER.query.filter(models.TWITTER.row_id == id).first()
        x = t.follower_ids(q.title)
        with open(os.path.join(EXPORTS_BASEDIR, '{}_followers_UUID_{}.txt'.format(q.title, export_uuid)), 'w+') as f:

            for u in x:
                    count = count + 1
                    f.write(u)
                    f.write('\n')
        addExportRef = models.EXPORTS(url='{}_followers_UUID_{}.txt'.format(q.title, export_uuid),type='Followers',exported=datetime.now(),count=count)
        q.exports.append(addExportRef)
        db.session.commit()
        db.session.close()