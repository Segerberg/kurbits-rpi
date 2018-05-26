from app import db, models
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from config import CONSUMER_KEY,CONSUMER_SECRET,ACCESS_TOKEN,ACCESS_SECRET
import twarc
def getTrends():
    CREDENTIALS = models.CREDENTIALS.query.one()
    loc = models.TRENDS_LOC.query.all()
    t = twarc.Twarc(consumer_key=CREDENTIALS.consumer_key,
                    consumer_secret=CREDENTIALS.consumer_secret,
                    access_token=CREDENTIALS.access_token,
                    access_token_secret=CREDENTIALS.access_secret)

    for location in loc:

        longLat =  ([x.strip() for x in location.loc.split(',')])
        print (longLat[0],longLat[1])
        woeidLookUp = (t.trends_closest(longLat[0],longLat[1]))

        for woeid in woeidLookUp:

            location.name = woeid['name']
            db.session.commit()

            for trend in t.trends_place(woeid['woeid']):

                for tag in (trend['trends']):

                    checkTrend = models.TWITTER_TRENDS.query.filter(models.TWITTER_TRENDS.name==tag['name']).filter(models.TWITTER_TRENDS.trend_loc==location.row_id).first()
                    checkTarget = models.TWITTER.query.filter(models.TWITTER.title==tag['name']).first()
                    if checkTrend == None:
                        if checkTarget == None:
                            addTrend = models.TWITTER_TRENDS(name=tag['name'],
                                                             promoted_content=tag['promoted_content'],
                                                             tweet_volume=tag['tweet_volume'],
                                                             url=tag['url'],collected=datetime.utcnow(),saved=False,
                                                             silence=False)
                        else:
                            addTrend = models.TWITTER_TRENDS(name=tag['name'],
                                                             promoted_content=tag['promoted_content'],
                                                             tweet_volume=tag['tweet_volume'],
                                                             url=tag['url'], collected=datetime.utcnow(), saved=True,
                                                             silence=False)

                        location.trends.append(addTrend)
                        db.session.commit()



