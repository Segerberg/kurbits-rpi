import os
from datetime import datetime
from config import EXPORTS_BASEDIR,CONSUMER_KEY,CONSUMER_SECRET,ACCESS_TOKEN,ACCESS_SECRET
from app import models, db, app
import uuid
import twarc

def Followers(id):
    CREDENTIALS = models.CREDENTIALS.query.one()
    with app.test_request_context():
        t = twarc.Twarc(consumer_key=CREDENTIALS.consumer_key,
                    consumer_secret=CREDENTIALS.consumer_secret,
                    access_token=CREDENTIALS.access_token,
                    access_token_secret=CREDENTIALS.access_secret)
        count = 0
        export_uuid = uuid.uuid4()
        if not os.path.isdir(EXPORTS_BASEDIR):
            os.makedirs(EXPORTS_BASEDIR)
        q = models.TWITTER.query.filter(models.TWITTER.row_id == id).first()
        x = t.follower_ids(q.title)
        with open(os.path.join(EXPORTS_BASEDIR, 'followers_{}.txt'.format(export_uuid)), 'w+') as f:

            for u in x:
                    count = count + 1
                    f.write(u)
                    f.write('\n')
        addExportRef = models.EXPORTS(url='followers_{}.txt'.format(export_uuid),type='Followers',exported=datetime.now(),count=count)
        q.exports.append(addExportRef)
        db.session.commit()
        db.session.close()