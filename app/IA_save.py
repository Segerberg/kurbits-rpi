'''
Script based on the work of oduwsdl/archivenow
https://github.com/oduwsdl/archivenow/blob/master/archivenow/handlers/ia_handler.py
'''

import requests
from datetime import datetime
from app import models, db

def push(id):
    tweet = models.SEARCH.query.get_or_404(id)
    uri_org = 'https://twitter.com/{}/status/{}'.format(tweet.username,tweet.tweet_id)
    msg = ''
    try:
        uri = 'https://web.archive.org/save/' + uri_org
        # push into the archive
        r = requests.get(uri, timeout=120, allow_redirects=True)
        r.raise_for_status()
        # extract the link to the archived copy
        if (r != None):
            if "Location" in r.headers:
                tweet.ia_uri = r.headers["Location"]
                tweet.ia_cap_count = tweet.ia_cap_count + 1
                tweet.ia_cap_date = datetime.now()
                db.session.commit()

            elif "Content-Location" in r.headers:
                tweet.ia_uri = "https://web.archive.org"+r.headers["Content-Location"]
                tweet.ia_cap_count = tweet.ia_cap_count + 1
                tweet.ia_cap_date = datetime.now()
                db.session.commit()

            else:
                for r2 in r.history:
                    if 'Location' in r2.headers:
                        tweet.ia_uri = r2.headers['Location']
                        tweet.ia_cap_count = tweet.ia_cap_count + 1
                        tweet.ia_cap_date = datetime.now()
                        db.session.commit()

                    if 'Content-Location' in r2.headers:
                        tweet.ia_uri = r2.headers['Content-Location']
                        tweet.ia_cap_count = tweet.ia_cap_count + 1
                        tweet.ia_cap_date = datetime.now()
                        db.session.commit()

        msg =  "No HTTP Location/Content-Location header is returned in the response"
    except Exception as e:
        if msg == '':
            msg = "Error: " + str(e)
        pass;

    return msg

def pushAccount(id):
    tweet = models.TWITTER.query.get_or_404(id)
    print (tweet.title)
    uri_org = 'https://twitter.com/{}'.format(tweet.title)
    msg = ''
    try:
        uri = 'https://web.archive.org/save/' + uri_org
        # push into the archive
        r = requests.get(uri, timeout=120, allow_redirects=True)
        r.raise_for_status()
        # extract the link to the archived copy
        if (r != None):
            if "Location" in r.headers:
                tweet.ia_uri = r.headers["Location"]
                tweet.ia_cap_count = tweet.ia_cap_count + 1
                tweet.ia_cap_date = datetime.now()
                db.session.commit()

            elif "Content-Location" in r.headers:
                tweet.ia_uri = "https://web.archive.org"+r.headers["Content-Location"]
                tweet.ia_cap_count = tweet.ia_cap_count + 1
                tweet.ia_cap_date = datetime.now()
                db.session.commit()

            else:
                for r2 in r.history:
                    if 'Location' in r2.headers:
                        tweet.ia_uri = r2.headers['Location']
                        tweet.ia_cap_count = tweet.ia_cap_count + 1
                        tweet.ia_cap_date = datetime.now()
                        db.session.commit()

                    if 'Content-Location' in r2.headers:
                        tweet.ia_uri = r2.headers['Content-Location']
                        tweet.ia_cap_count = tweet.ia_cap_count + 1
                        tweet.ia_cap_date = datetime.now()
                        db.session.commit()

        msg =  "No HTTP Location/Content-Location header is returned in the response"
    except Exception as e:
        if msg == '':
            msg = "Error: " + str(e)
        pass;

    return msg