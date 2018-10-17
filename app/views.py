#!/usr/bin/env python
# -*- coding: utf-8 -*-
from app import app, render_template, request,db, url_for, redirect,flash,Response,jsonify, send_from_directory,g
from app import models
from .forms import twitterTargetForm, twitterTargetUserForm, SearchForm, twitterCollectionForm, collectionAddForm, twitterTrendForm, stopWordsForm, scheduleForm,SCHEDULE_CHOICES, passwordForm, collectionTypeForm, langCodeForm, networkForm,credForm,twitterTrendWoeidForm, indexTweetForm
from sqlalchemy.exc import IntegrityError
from .twarcUIarchive import twittercrawl
from .twitterTrends import getTrends
from .getFollowers import Followers
from .hashtags import hashTags, hashTagsCollection
from .topusers import topUsers, topUsersCollection
from .dehydrate import dehydrateUserSearch,dehydrateCollection
from .index_tweets import indexUserSearch
from .wordcloud import wordCloud, wordCloudCollection
from .urls import urlsUserSearch, urlsCollection
from .tweets2csv import csvUserSearch, csvCollection
from.network import networkUserSearch
from .scheduleCollection import startScheduleCollectionCrawl
from .IA_save import push, pushAccount
from .media2warc import media2warc
from .url2warc import url2warc
from config import POSTS_PER_PAGE, REDIS_DB, MAP_VIEW,MAP_ZOOM,TARGETS_PER_PAGE,EXPORTS_BASEDIR,ARCHIVE_BASEDIR, TREND_UPDATE, SQLALCHEMY_DATABASE_URI, BACKUP_BASEDIR
from datetime import datetime, timedelta
from redis import Redis
from rq import Queue
from rq.worker import Worker
from rq_scheduler import Scheduler
import os
import shutil
import psutil
import uuid
from .bagger import bagger
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import sqlalchemy
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import subprocess
from .decorators import async
from .scripts import humansize, delIndex, vac, backup_db, deleteindextweets
auth = HTTPBasicAuth()
q = Queue(connection=Redis())
eq = Queue('internal',connection=Redis())
scheduler = Scheduler(connection=Redis())

@app.before_first_request
def before_first_request():
    COLLECTIONS = models.COLLECTION.query.all()

    '''for collection in COLLECTIONS:
        if collection.schedule:
            scheduler.cancel(collection.schedule)
            scheduler.schedule(
                scheduled_time=datetime.utcnow(),  # Time for first execution, in UTC timezone
                func=startScheduleCollectionCrawl,  # Function to be queued
                args=[collection.row_id],
                interval=collection.scheduleInterval,  # Time before the function is called again, in seconds
                repeat=None,  # Repeat this number of times (None means repeat forever)
                id=collection.schedule
            )
            collection.nextRun = datetime.now() + timedelta(seconds=int(collection.scheduleInterval))
            db.session.commit()'''


    scheduler.cancel('trendSchedule')
    scheduler.schedule(
        scheduled_time=datetime.utcnow(),
        func=getTrends,
        interval=TREND_UPDATE,
        repeat=None,
        id='trendSchedule'
    )


@app.before_request
def before_request():
        g.search_form = SearchForm()



def queryUser():
    users = db.session.query(models.USERS.user,models.USERS.passw).all()
    return dict(users)

@auth.verify_password
def verify_password(username, password):
    if username in queryUser():
        return check_password_hash(queryUser().get(username), password)
    return False

'''INDEX ROUTE'''
@app.route('/')
@app.route('/index', methods=['GET', 'POST'])
@auth.login_required
def index():
    twitterUserCount = models.TWITTER.query.filter(models.TWITTER.status == '1').filter(models.TWITTER.targetType=='User').count()
    twitterSearchCount = models.TWITTER.query.filter(models.TWITTER.status == '1').filter(models.TWITTER.targetType == 'Search').count()
    collectionCount = models.COLLECTION.query.filter(models.COLLECTION.status=='1').count()
    trendsCount = db.session.query(models.TRENDS_LOC).count()
    CRAWLLOG = models.CRAWLLOG.query.order_by(models.CRAWLLOG.row_id.desc()).limit(10).all()
    search_form = SearchForm()
    if request.method == 'POST':
        return redirect((url_for('search_results', form=search_form, query=search_form.search.data)))

    return render_template("index.html", twitterUserCount=twitterUserCount, twitterSearchCount=twitterSearchCount, collectionCount=collectionCount,trendsCount=trendsCount, CRAWLLOG=CRAWLLOG,  qlen=len(q), search_form=search_form, auth=auth.username())


'''SEARCH'''
@app.route('/search', methods=['GET', 'POST'])
@auth.login_required
def search():
    search_form =SearchForm()
    if request.method == 'POST':
        return redirect((url_for('search_results', search_form=search_form, query=search_form.search.data, page=1)))
    return render_template("search.html", search_form=search_form)


'''SEARCH RESULTS'''
@app.route('/search/<query>/<int:page>', methods=['GET', 'POST'])
@auth.login_required
def search_results(query,page=1):
    search_form = SearchForm()
    results = models.SEARCH.query.filter(models.SEARCH.text.like(u'%{}%'.format(query))).paginate(page, POSTS_PER_PAGE, False)
    return render_template('search.html', query=query, results=results,search_form=search_form)

'''
TWITTER
'''

'''USER-TIMELINES'''
@app.route('/twittertargets/<int:page>', methods=['GET', 'POST'])
@auth.login_required
def twittertargets(page=1):
    TWITTER = models.TWITTER.query.filter(models.TWITTER.targetType =='User').filter(models.TWITTER.status == '1').order_by(models.TWITTER.title).paginate(page, TARGETS_PER_PAGE,False)
    form = twitterTargetUserForm(prefix='form')

    if request.method == 'POST'and form.validate_on_submit():

        try:


            addTarget = models.TWITTER(title=form.title.data, searchString='', searchLang=None,creator=form.creator.data, targetType='User',
                                       description=form.description.data, subject=form.subject.data, status=form.status.data,lastCrawl=None, totalTweets=0,
                                       added=datetime.now(), woeid=None, index=form.index.data, mediaHarvest=form.mediaHarvest.data, url_harvest=form.urlHarvest.data,schedule=None, scheduleInterval=None, scheduleText = None,
                                       ia_uri=None, ia_cap_count=0, ia_cap_date=None)

            addLog = models.CRAWLLOG(tag_title=form.title.data,event_start=datetime.utcnow(), event_text='Target added',event_description=None)
            addTarget.logs.append(addLog)
            db.session.add(addTarget)
            db.session.commit()
            db.session.close()
            back = models.TWITTER.query.filter(models.TWITTER.title == form.title.data).first()
            return redirect(url_for('twittertargetDetail', id=back.row_id))
        except IntegrityError:
            flash(u'Twitter user account already in database!', 'danger')
            db.session.rollback()

    return render_template("twittertargets.html", TWITTER=TWITTER, form=form)

'''USER-TIMELINES-CLOSED'''
@app.route('/twittertargetsclosed/<int:page>', methods=['GET', 'POST'])
@auth.login_required
def twittertargetsclosed(page=1):
    TWITTER = models.TWITTER.query.filter(models.TWITTER.targetType=='User').filter(models.TWITTER.status=='0').order_by(models.TWITTER.title).paginate(page, TARGETS_PER_PAGE,False)
    form = twitterTargetUserForm(prefix='form')

    if request.method == 'POST'and form.validate_on_submit():

        try:
            addTarget = models.TWITTER(title=form.title.data, searchString='',searchLang=None, creator=form.creator.data, targetType='User',
                                       description=form.description.data, subject=form.subject.data, status=form.status.data,lastCrawl=None, totalTweets=0,
                                       added=datetime.now(), woeid=None, index=form.index.data, mediaHarvest=form.mediaHarvest.data,url_harvest=form.urlHarvest.data,
                                       schedule=None, scheduleInterval=None, scheduleText = None,ia_uri=None,ia_cap_count=0, ia_cap_date=None)

            addLog = models.CRAWLLOG(tag_title=form.title.data,event_start=datetime.utcnow(), event_text='Target added',event_description=None)
            addTarget.logs.append(addLog)
            db.session.add(addTarget)
            db.session.commit()
            db.session.close()
            back = models.TWITTER.query.filter(models.TWITTER.title == form.title.data).first()
            return redirect(url_for('twittertargetDetail', id=back.row_id))
        except IntegrityError:
            flash(u'Twitter user account already in database!', 'danger')
            db.session.rollback()

    return render_template("twittertargets.html", TWITTER=TWITTER, form=form, closed = True)



'''TRENDS'''
@app.route('/twittertrends', methods=['GET', 'POST'])
@auth.login_required
def twittertrends():
    filterTime = datetime.utcnow() - timedelta(minutes=60)
    loc = models.TRENDS_LOC.query.all()
    trend = models.TWITTER_TRENDS.query.filter(models.TWITTER_TRENDS.collected > filterTime).all()
    trendAll = models.TWITTER_TRENDS.query.order_by(models.TWITTER_TRENDS.collected.desc()).all()
    trendForm = twitterTrendForm(prefix='trendform')
    woeidForm =twitterTrendWoeidForm(prefix='woeidForm')

    form = twitterTargetForm(prefix='form')
    schedForm = scheduleForm(prefix='schedForm')

    if request.method == 'POST' and woeidForm.validate_on_submit():
        addloc = models.TRENDS_LOC(name=None, loc=None, woeid=woeidForm.woeidCode.data)
        db.session.add(addloc)
        db.session.commit()
        eq.enqueue(getTrends)
        return redirect((url_for('twittertrends')))


    if request.method == 'POST' and trendForm.validate_on_submit():
        addloc = models.TRENDS_LOC(name=None,loc=trendForm.geoloc.data, woeid=None)
        db.session.add(addloc)
        db.session.commit()
        eq.enqueue(getTrends)
        flash(u'Trend location added!', 'success')
        return redirect((url_for('twittertrends')))

    if request.method == 'POST' and not trendForm.validate_on_submit():
        flash(u'Not a valid location!', 'danger')
        return redirect((url_for('twittertrends')))

    return render_template("trends.html", loc=loc, trend=trend, trendForm=trendForm, form=form, woeidForm = woeidForm, trendAll=trendAll, MAP_VIEW = MAP_VIEW, MAP_ZOOM=MAP_ZOOM)



"""Route to add Trend to Search"""
@app.route('/addtwittertrend/<id>', methods=['GET', 'POST'])
@auth.login_required
def addtwittertrend(id):
    trendAll = models.TWITTER_TRENDS.query.all()
    if request.method == 'POST':
        addTarget = models.TWITTER(title=id, searchString=id, searchLang=None,
                                   creator='', targetType='Search',
                                   description='[Added from trends]', subject='',
                                   status='1', lastCrawl=None, totalTweets=0,
                                   added=datetime.now(), woeid=None, index='0',mediaHarvest='0',
                                   url_harvest='0',
                                   schedule=None, scheduleInterval=None, scheduleText = None,
                                   ia_uri=None,ia_cap_count=0,ia_cap_date=None)

        addLog = models.CRAWLLOG(tag_title=id, event_start=datetime.utcnow(), event_text='Target added',event_description=None)
        for t in trendAll:
            if t.name == id:
                t.saved= True

        addTarget.logs.append(addLog)
        db.session.add(addTarget)
        db.session.commit()
        db.session.close()
        TWITTER = models.TWITTER.query.filter(models.TWITTER.title == id).first()
        return redirect((url_for('twittertargetDetail', id=TWITTER.row_id)))


"""Route to clear Trends"""
@app.route('/cleartwittertrend/<id>', methods=['GET', 'POST'])
@auth.login_required
def cleartwittertrend(id):
    trendAll = models.TRENDS_LOC.query.filter(models.TRENDS_LOC.row_id==id).all()
    print (request.url_rule)
    for t in trendAll:
        for trend in t.trends:
            if trend.saved == False and trend.silence == False:
                db.session.delete(trend)
    db.session.commit()
    return redirect((url_for('twittertrends')))


"""Route to delete Trend Location"""
@app.route('/deletetrendlocation/<id>', methods=['GET', 'POST'])
@auth.login_required
def deleteTrendLocation(id):
    trendLocation = models.TRENDS_LOC.query.filter(models.TRENDS_LOC.row_id==id).first()
    db.session.delete(trendLocation)
    db.session.commit()
    return redirect((url_for('twittertrends')))

"""Route to delete Trend Location"""
@app.route('/silencetrend/<id>', methods=['GET', 'POST'])
@auth.login_required
def silenceTrend(id):
    if '/vocabs' in request.referrer:
        trend = models.TWITTER_TRENDS.query.get_or_404(id)
        trend.silence = False
        db.session.commit()
    else:
        trend = models.TWITTER_TRENDS.query.get_or_404(id)
        trend.silence = True
        db.session.commit()

    return redirect(request.referrer)

"""Route for altering collection types"""
@app.route('/collectionstype/<type>/<id>', methods=['GET', 'POST'])
@auth.login_required
def alterCollectionType(type, id):
    if type == 'add':
        typeForm = collectionTypeForm()
        type = models.VOCABS(term=typeForm.type.data,use='collectionType',description=None)
        db.session.add(type)
        db.session.commit()
    else:
        type = models.VOCABS.query.get_or_404(id)
        db.session.delete(type)
        db.session.commit()

    return redirect(request.referrer)
"""Route for altering langcode"""
@app.route('/langcode/<type>/<id>', methods=['GET', 'POST'])
@auth.login_required
def alterLangCode(type, id):
    if type == 'add':
        langForm = langCodeForm()
        if len(langForm.type.data) > 2 :
            flash(u'Sorry not a valid language code! ', 'danger')
        else:
            langcode = models.VOCABS(term=langForm.type.data,use='langcode',description=None)
            db.session.add(langcode)
            db.session.commit()
            flash(u'Added {} to language codes'.format(langForm.type.data), 'success')

    else:
        langcode = models.VOCABS.query.get_or_404(id)
        db.session.delete(langcode)
        db.session.commit()

    return redirect(request.referrer)

"""Route to remove Trend from Search"""
@app.route('/removetwittertrend/<id>', methods=['GET', 'POST'])
@auth.login_required
def removetwittertrend(id):
    trendAll = models.TWITTER_TRENDS.query.all()
    if request.method == 'POST':
        for t in trendAll:
            if t.name == id:
                db.session.delete(t)
        db.session.commit()
    return redirect((url_for('twittertrends')))

"""Route to refresh trends """
@app.route('/refreshtwittertrend', methods=['GET', 'POST'])
@auth.login_required
def refreshtwittertrend():
    eq.enqueue(getTrends)
    return redirect((url_for('twittertrends')))


'''API-SEARCH-TARGETS'''
@app.route('/twittersearchtargets/<int:page>', methods=['GET', 'POST'])
@auth.login_required
def twittersearchtargets(page=1):
    TWITTER = models.TWITTER.query.filter(models.TWITTER.targetType == 'Search').filter(models.TWITTER.status=='1').order_by(models.TWITTER.title).paginate(page, TARGETS_PER_PAGE, False)
    templateType = "Search"
    openClosed = "Open"
    collectionForm = twitterCollectionForm(prefix='collectionForm')
    langChoices = [(c.term, c.term) for c in models.VOCABS.query.filter(models.VOCABS.use == 'langcode').order_by(models.VOCABS.term.asc()).all()]
    form = twitterTargetForm(prefix='form')
    form.searchLang.choices = langChoices
    if request.method == 'POST'and form.validate_on_submit():
        try:
            addTarget = models.TWITTER(title=form.title.data, searchString=form.searchString.data,searchLang=form.searchLang.data, creator=form.creator.data, targetType='Search',
                                       description=form.description.data, subject=form.subject.data,
                                       status=form.status.data, lastCrawl=None, totalTweets=0,
                                       added=datetime.now(), woeid=None, index=form.index.data,
                                       mediaHarvest=form.mediaHarvest.data,url_harvest=form.urlHarvest.data,
                                       schedule=None, scheduleInterval=None, scheduleText = None,
                                       ia_uri=None,ia_cap_count=0,ia_cap_date=None)
            addLog = models.CRAWLLOG(tag_title=form.title.data, event_start=datetime.utcnow(), event_text='Target added',event_description=None)
            addTarget.logs.append(addLog)
            db.session.add(addTarget)
            db.session.commit()
            db.session.close()
            back = models.TWITTER.query.filter(models.TWITTER.title == form.title.data).first()
            return redirect(url_for('twittertargetDetail', id=back.row_id))

        except IntegrityError:
            flash(u'Search is already in database! ', 'danger')
            db.session.rollback()

    return render_template("twittertargets.html", TWITTER=TWITTER, form=form, templateType = templateType)

'''API-SEARCH-TARGETS-CLOSED'''
@app.route('/twittersearchtargetsclosed/<int:page>', methods=['GET', 'POST'])
@auth.login_required
def twittersearchtargetsclosed(page=1):
    TWITTER = models.TWITTER.query.filter(models.TWITTER.targetType == 'Search').filter(models.TWITTER.status=='0').order_by(models.TWITTER.title).paginate(page, TARGETS_PER_PAGE, False)
    templateType = "Search"
    langChoices = [(c.term, c.term) for c in models.VOCABS.query.filter(models.VOCABS.use == 'langcode').order_by(models.VOCABS.term.asc()).all()]
    form = twitterTargetForm(prefix='form')
    form.searchLang.choices = langChoices
    if request.method == 'POST'and form.validate_on_submit():
        try:
            addTarget = models.TWITTER(title=form.title.data, searchString=form.searchString.data, searchLang=form.searchLang.data, creator=form.creator.data, targetType='Search',
                                       description=form.description.data, subject=form.subject.data,
                                       status=form.status.data, lastCrawl=None, totalTweets=0,
                                       added=datetime.now(), woeid=None, index=form.index.data, mediaHarvest=form.mediaHarvest.data,
                                       url_harvest=form.urlHarvest.data,
                                       schedule=None, scheduleInterval=None, scheduleText = None,
                                       ia_uri=None,ia_cap_count=0,ia_cap_date=None)
            addLog = models.CRAWLLOG(tag_title=form.title.data, event_start=datetime.now(), event_text='Target added',event_description=None)
            addTarget.logs.append(addLog)
            db.session.add(addTarget)
            db.session.commit()
            db.session.close()
            back = models.TWITTER.query.filter(models.TWITTER.title == form.title.data).first()
            return redirect(url_for('twittertargetDetail', id=back.row_id))

        except IntegrityError:
            flash(u'Search is already in database! ', 'danger')
            db.session.rollback()

    return render_template("twittertargets.html", TWITTER=TWITTER, form=form, templateType = templateType, closed=True)

'''COLLECTIONS'''
@app.route('/collections/<int:page>', methods=['GET', 'POST'])
@auth.login_required
def collections(page=1):
    COLLECTIONS = models.COLLECTION.query.filter(models.COLLECTION.status == '1').order_by(models.COLLECTION.title).paginate(page, TARGETS_PER_PAGE, False)
    choices = [(c.term, c.term) for c in models.VOCABS.query.filter(models.VOCABS.use == 'collectionType').all()]
    collectionForm = twitterCollectionForm(prefix='collectionForm')
    collectionForm.collectionType.choices = choices
    if request.method == 'POST' and collectionForm.validate_on_submit():
        try:
            addTarget = models.COLLECTION(title=collectionForm.title.data, curator=collectionForm.curator.data,
                                       collectionType=collectionForm.collectionType.data,
                                       description=collectionForm.description.data, subject=collectionForm.subject.data,
                                       status=collectionForm.status.data, inclDateStart=collectionForm.inclDateStart.data,
                                       inclDateEnd=collectionForm.inclDateStart.data, lastCrawl=None,
                                       totalTweets=0, added=datetime.now(),schedule=None, scheduleInterval=None, scheduleText = None, nextRun=None)

            #addLog = models.CRAWLLOG(tag_title=form.title.data, event_start=datetime.now(),
            #                         event_text='ADDED TO DB')
            #addTarget.logs.append(addLog)
            db.session.add(addTarget)
            db.session.commit()
            db.session.close()
            back = models.COLLECTION.query.filter(models.COLLECTION.title == collectionForm.title.data).first()
            return redirect(url_for('collectionDetail', id=back.row_id, page=1))

        except IntegrityError:
            flash(u'Collection name is already in use! ', 'danger')
            db.session.rollback()


    return render_template("collections.html", COLLECTIONS=COLLECTIONS, collectionForm=collectionForm)


'''Route to view archived user tweets '''
@app.route('/usertweets/<id>/<int:page>', methods=['GET', 'POST'])
@auth.login_required
def userlist(id,page=1):
    id=id
    print (id)
    results = models.SEARCH.query.filter(models.SEARCH.username==id).order_by(models.SEARCH.created_at.desc()).paginate(page, POSTS_PER_PAGE, False)
    twitterTarget = models.TWITTER.query.filter(models.TWITTER.title == id).first()
    form = twitterTargetUserForm(prefix='form')
    if request.method == 'POST' and form.validate_on_submit():

        try:
            addTarget = models.TWITTER(title=form.title.data,searchString='', searchLang=None,creator=form.creator.data, targetType='User',
                                       description=form.description.data, subject=form.subject.data,
                                       status=form.status.data, lastCrawl=None, totalTweets=0,
                                       added=datetime.now(), woeid=None, index=form.index.data,
                                       mediaHarvest=form.mediaHarvest.data,url_harvest=form.urlHarvest.data,
                                       schedule=None, scheduleInterval=None , scheduleText = None,
                                       ia_uri=None, ia_cap_count=0,ia_cap_date=None)

            addLog = models.CRAWLLOG(tag_title=form.title.data, event_start=datetime.now(), event_text='Target added',event_description=None)
            addTarget.logs.append(addLog)
            db.session.add(addTarget)
            db.session.commit()
            db.session.close()
            backref = models.TWITTER.query.filter(models.TWITTER.title == form.title.data).first()

        except IntegrityError:
            flash(u'Twitter user account already in database ', 'danger')
            db.session.rollback()
        return redirect(url_for('twittertargetDetail', id=backref.row_id))



    return render_template("usertweets.html", results=results,id=id, twitterTarget=twitterTarget,form=form)

'''Route to view IA archived user tweets '''
@app.route('/ia_tweets/<id>/<int:page>', methods=['GET', 'POST'])
@auth.login_required
def IA_tweets(id,page=1):
    twitterTarget = models.TWITTER.query.filter(models.TWITTER.title == id).first()
    results = models.SEARCH.query.filter(models.SEARCH.username==id).filter(models.SEARCH.ia_uri != None).order_by(models.SEARCH.ia_cap_date.desc()).paginate(page, 100, False)
    return render_template("ia_tweets.html", results=results, id=id, twitterTarget=twitterTarget)


'''Route to view IA archived search-api target tweets '''
@app.route('/ia_search_tweets/<id>/<int:page>', methods=['GET', 'POST'])
@auth.login_required
def IA_search_tweets(id,page=1):
    twitterTarget = models.TWITTER.query.filter(models.TWITTER.row_id == id).first()
    results = models.SEARCH.query.filter(models.SEARCH.source == id).filter(models.SEARCH.ia_uri != None).order_by(
        models.SEARCH.ia_cap_date.desc()).paginate(page, 100, False)

    return render_template("ia_search_tweets.html", results=results, id=id, twitterTarget=twitterTarget)


'''Route to view archived user tweets from twitter searches '''
@app.route('/searchtweets/<id>/<int:page>', methods=['GET', 'POST'])
@auth.login_required
def searchlist(id, page=1):
    id=id
    results = models.SEARCH.query.filter(models.SEARCH.source==id).order_by(models.SEARCH.created_at.desc()).paginate(page, POSTS_PER_PAGE, False)
    twitterTarget = models.TWITTER.query.filter(models.TWITTER.row_id == id).first()
    form = twitterTargetForm(prefix='form')
    if request.method == 'POST' and form.validate_on_submit():
        try:
            addTarget = models.TWITTER(title=form.title.data,searchString='',searchLang=None ,creator=form.creator.data, targetType='User',
                                       description=form.description.data, subject=form.subject.data,
                                       status=form.status.data, lastCrawl=None, totalTweets=0,
                                       added=datetime.now(), woeid=None, index=form.index.data,
                                       mediaHarvest=form.mediaHarvest.data,url_harvest=form.urlHarvest.data,
                                       schedule=None, scheduleInterval=None , scheduleText = None,
                                       ia_uri=None, ia_cap_count=0,ia_cap_date=None)
            addLog = models.CRAWLLOG(tag_title=form.title.data, event_start=datetime.now(), event_text='Target added',event_description=None)
            addTarget.logs.append(addLog)
            db.session.add(addTarget)
            db.session.commit()
            db.session.close()

        except IntegrityError:
            flash(u'Twitter user account already in database ', 'danger')
            db.session.rollback()
        return redirect(url_for('twittertargets'))



    return render_template("usertweets.html", results=results,id=id, twitterTarget=twitterTarget,form=form)

'''Route to detail view of twitter user/search target'''
@app.route('/twittertargetsdetail/<id>', methods=['GET', 'POST'])
@auth.login_required
def twittertargetDetail(id):

    TWITTER = models.TWITTER.query.filter(models.TWITTER.row_id == id).first()
    object = models.TWITTER.query.get_or_404(id)
    CRAWLLOG = models.CRAWLLOG.query.order_by(models.CRAWLLOG.event_start.desc()).filter(models.CRAWLLOG.tag_id==id).limit(100)
    EXPORTS = models.EXPORTS.query.order_by(models.EXPORTS.row_id.desc()).filter(models.EXPORTS.twitter_id==id)
    SEARCH = models.SEARCH.query.filter(models.SEARCH.username==TWITTER.title).filter(models.SEARCH.ia_uri != None ).limit(5)
    SEARCH_SEARCH = models.SEARCH.query.filter(models.SEARCH.source==id).filter(models.SEARCH.ia_uri != None).limit(5)
    searchCount =  models.SEARCH.query.filter(models.SEARCH.source == id).count()
    langChoices = [(c.term, c.term) for c in models.VOCABS.query.filter(models.VOCABS.use == 'langcode').order_by(models.VOCABS.term.asc()).all()]
    userForm = twitterTargetUserForm(prefix='userform', obj=object)
    form = twitterTargetForm(prefix='form', obj=object)
    form.searchLang.choices = langChoices
    assForm = collectionAddForm(prefix="assForm")
    netForm = networkForm(prefix="netForm")
    indexForm = indexTweetForm(prefix='indexForm')
    linkedCollections = models.TWITTER.query. \
        filter(models.TWITTER.row_id == id). \
        first(). \
        tags
    l = []
    fileList = []
    warcList = []
    try:
        for filename in os.listdir(os.path.join(ARCHIVE_BASEDIR,TWITTER.targetType,TWITTER.title[0],TWITTER.title)):
            print (filename)
            if filename.endswith("json.gz"):
                try:
                    mtime = os.path.getmtime(os.path.join(ARCHIVE_BASEDIR,TWITTER.targetType,TWITTER.title[0],TWITTER.title,filename))
                except OSError:
                    mtime = 0
                last_modified_date = datetime.fromtimestamp(mtime)
                x = dict(fname=filename, fsize=humansize(os.path.getsize(os.path.join(ARCHIVE_BASEDIR,TWITTER.targetType,TWITTER.title[0],TWITTER.title,filename))), fdate=last_modified_date)
                fileList.append(x)
            elif filename.endswith("warc.gz"):
                try:
                    mtime = os.path.getmtime(os.path.join(ARCHIVE_BASEDIR,TWITTER.targetType,TWITTER.title[0],TWITTER.title,filename))
                except OSError:
                    mtime = 0
                last_modified_date = datetime.fromtimestamp(mtime)
                x = dict(fname=filename, fsize=humansize(os.path.getsize(os.path.join(ARCHIVE_BASEDIR,TWITTER.targetType,TWITTER.title[0],TWITTER.title,filename))), fdate=last_modified_date)
                warcList.append(x)


    except:
        pass
    sortedFilelist = sorted(fileList, key=lambda k: k['fname'])
    sortedWarclist = sorted(warcList, key=lambda k: k['fname'])
    print (sortedFilelist)
    if request.method == 'POST' and assForm.validate_on_submit():
        object.tags.append(assForm.assoc.data)
        db.session.commit()
        return redirect(url_for('twittertargetDetail', id=id))

    if request.method == 'POST' and indexForm.validate_on_submit():
        eq.enqueue(indexUserSearch, id=id, dateStart=indexForm.inclDateStart.data,
                   dateStop=indexForm.inclDateEnd.data, RT=indexForm.retweets.data)


    if request.method == 'POST' and netForm.validate_on_submit():
        if netForm.min_subgraph_size.data:
            min_subgraph = netForm.min_subgraph_size.data
        else:
            min_subgraph = False

        if netForm.max_subgraph_size.data:
            max_subgraph = netForm.max_subgraph_size.data
        else:
            max_subgraph = False



        eq.enqueue(networkUserSearch, id=id, users=netForm.users.data,retweets=netForm.retweets.data, output=netForm.output.data,min_subgraph_size=min_subgraph, max_subgraph_size=max_subgraph , timeout=3000)


        flash(u'Exporting network, please refresh page!', 'success')
        return redirect(url_for('twittertargetDetail', id=id))


    if request.method == 'POST' and form.validate_on_submit():
        try:
            form.populate_obj(object)
            addLog = models.CRAWLLOG(tag_title=form.title.data, event_start=datetime.now(), event_text='Description modified',
                                     event_description=None)
            object.logs.append(addLog)
            db.session.add(object)
            db.session.commit()
            db.session.close()
            flash(u'Record saved! ', 'success')
        except IntegrityError:
            flash(u'Twitter user account already in database ', 'danger')
            db.session.rollback()
        return redirect(url_for('twittertargetDetail',id=id))

    if request.method == 'POST' and userForm.validate_on_submit():
        try:
            userForm.populate_obj(object)
            addLog = models.CRAWLLOG(tag_title=userForm.title.data, event_start=datetime.now(),
                                     event_text='Description modified',event_description=None)
            object.logs.append(addLog)
            db.session.add(object)
            db.session.commit()
            db.session.close()
            flash(u'Record saved! ', 'success')
        except IntegrityError:
            flash(u'Twitter user account already in database ', 'danger')
            db.session.rollback()

        return redirect(url_for('twittertargetDetail', id=id))

    return render_template("twittertargetdetail.html", TWITTER=TWITTER, fileList = sortedFilelist, warcList=sortedWarclist, form=form,
                           userForm=userForm,netForm=netForm, indexForm = indexForm, CRAWLLOG=CRAWLLOG,
                           EXPORTS=EXPORTS, SEARCH = SEARCH, SEARCH_SEARCH=SEARCH_SEARCH,searchCount=searchCount ,linkedCollections=linkedCollections,
                           assForm=assForm, l=l, ref = request.referrer)

'''
Route to run media2warc harvest
'''
@app.route('/mediawarc/<id>/<filename>')
@auth.login_required
def mediawarc(id,filename):
    eq.enqueue(media2warc,id,filename,timeout=86400)
    flash(u'Started media harvest! ', 'success')

    return redirect(url_for('twittertargetDetail', id=id))

'''
Route to run utl2warc harvest for all tweet files
'''
@app.route('/allmediawarc/<id>')
@auth.login_required
def allmediawarc(id):
    fileList = []
    countFiles = 0
    TWITTER = models.TWITTER.query.get_or_404(id)
    for filename in os.listdir(os.path.join(ARCHIVE_BASEDIR,TWITTER.targetType,TWITTER.title[0],TWITTER.title)):
        if filename.endswith('.media.warc.gz'):
            fileList.append(filename.replace('.media.warc.gz','.json.gz'))
    for filename in os.listdir(os.path.join(ARCHIVE_BASEDIR,TWITTER.targetType,TWITTER.title[0],TWITTER.title)):
        if filename.endswith('.json.gz') and filename not in fileList:
            eq.enqueue(media2warc,id,filename,timeout=86400)
            countFiles += 1
    if countFiles == 0:
        flash(u'No new files to harvest! '.format(countFiles), 'warning')
    else:
        flash(u'Started media harvest for {} files! '.format(countFiles), 'success')
    return redirect(url_for('twittertargetDetail', id=id))


'''
Route to run url2warc harvest
'''
@app.route('/urlwarc/<id>/<filename>')
@auth.login_required
def urlwarc(id,filename):
    eq.enqueue(url2warc,id,filename,timeout=86400)
    flash(u'Started url harvest! ', 'success')
    return redirect(url_for('twittertargetDetail', id=id))

'''
Route to run utl2warc harvest for all tweet files
'''
@app.route('/allurlwarc/<id>')
@auth.login_required
def allurlwarc(id):
    fileList = []
    countFiles = 0
    TWITTER = models.TWITTER.query.get_or_404(id)
    for filename in os.listdir(os.path.join(ARCHIVE_BASEDIR,TWITTER.targetType,TWITTER.title[0],TWITTER.title)):
        if filename.endswith('.urls.warc.gz'):
            fileList.append(filename.replace('.urls.warc.gz','.json.gz'))
    for filename in os.listdir(os.path.join(ARCHIVE_BASEDIR,TWITTER.targetType,TWITTER.title[0],TWITTER.title)):
        if filename.endswith('.json.gz') and filename not in fileList:
            eq.enqueue(url2warc,id,filename,timeout=86400)
            countFiles += 1
    if countFiles == 0:
        flash(u'No new files to harvest! '.format(countFiles), 'warning')
    else:
        flash(u'Started url harvest for {} files! '.format(countFiles), 'success')
    return redirect(url_for('twittertargetDetail', id=id))


'''
Route to delete tweet and warc files  
'''
@app.route('/deletefile/<id>/<filename>')
@auth.login_required
def deletefile(id,filename):
    import gzip
    TWITTER = models.TWITTER.query.get_or_404(id)
    try:
        tweetCount = 0
        for line in gzip.open(os.path.join(ARCHIVE_BASEDIR,TWITTER.targetType,TWITTER.title[0],TWITTER.title, filename)):
            tweetCount = tweetCount + 1
        os.remove(os.path.join(ARCHIVE_BASEDIR,TWITTER.targetType,TWITTER.title[0],TWITTER.title,filename))
        flash(u'Archive file deleted!', 'success')
        addLog = models.CRAWLLOG(tag_title=TWITTER.title, event_start=datetime.now(),
                                 event_text='Archive file deleted',
                                 event_description=None)
        TWITTER.logs.append(addLog)
        TWITTER.totalTweets = TWITTER.totalTweets - tweetCount
        db.session.commit()
        db.session.close()
    except:
        flash(u'Archive file could not be deleted!', 'danger')
        pass

    return redirect(request.referrer)


'''Route to detail view of collections'''
@app.route('/collectiondetail/<id>/<int:page>', methods=['GET', 'POST'])
@auth.login_required
def collectionDetail(id, page=1):
    object = models.COLLECTION.query.get_or_404(id)
    #targets = models.TWITTER.query.all()
    EXPORTS = models.EXPORTS.query.order_by(models.EXPORTS.row_id.desc()).filter(models.EXPORTS.collection_id == id)
    #CRAWLLOG = models.CRAWLLOG.query.order_by(models.CRAWLLOG.row_id.desc()).filter(models.CRAWLLOG.tag_id==id)
    #TWITTER = models.TWITTER.query.filter(models.TWITTER.status == '1').filter(models.TWITTER.targetType == 'User').order_by(models.TWITTER.title).paginate(page, TARGETS_PER_PAGE, False)
    linkedTargets =  models.COLLECTION.query.filter(models.COLLECTION.row_id==id).first().tags.paginate(page, POSTS_PER_PAGE, False)
    choices = [(c.term, c.term) for c in models.VOCABS.query.filter(models.VOCABS.use == 'collectionType').all()]

    collectionForm = twitterCollectionForm(prefix='collectionform',obj=object)
    collectionForm.collectionType.choices = choices
    targetForm = twitterTargetUserForm(prefix='targetform')
    searchApiForm = twitterTargetForm(prefix='searchapiform')
    langChoices = [(c.term, c.term) for c in models.VOCABS.query.filter(models.VOCABS.use == 'langcode').order_by(models.VOCABS.term.asc()).all()]
    searchApiForm.searchLang.choices = langChoices
    schedForm = scheduleForm(prefix="schedForm")

    if request.method == 'POST' and schedForm.validate_on_submit():
        jobId = str(uuid.uuid4())
        if object.schedule:
            scheduler.cancel(object.schedule)
        object.schedule = jobId
        object.scheduleText = dict(SCHEDULE_CHOICES).get(schedForm.schedule.data)
        object.scheduleInterval = schedForm.schedule.data
        object.nextRun = datetime.now() + timedelta(seconds=int(schedForm.schedule.data))
        print(schedForm.schedule.data)
        scheduler.schedule(
            scheduled_time=datetime.utcnow(),  # Time for first execution, in UTC timezone
            func=startScheduleCollectionCrawl,  # Function to be queued
            args=[id],
            interval=schedForm.schedule.data,  # Time before the function is called again, in seconds
            repeat=None, # Repeat this number of times (None means repeat forever)
            id=jobId
        )

        db.session.commit()
        flash(u'Scheduled Collection', 'success')
    else:
        print (schedForm.errors.items())


    if request.method == 'POST' and collectionForm.validate_on_submit():
        try:
            collectionForm.populate_obj(object)
            db.session.add(object)
            db.session.commit()
            db.session.close()
            flash(u'Record saved! ', 'success')
        except IntegrityError:
            flash(u'Collection name is already in use!  ', 'danger')
            db.session.rollback()
        return redirect(url_for('collectionDetail',id=id, page=1))

    if request.method == 'POST' and targetForm.validate_on_submit():
        try:
            addTarget = models.TWITTER(title=targetForm.title.data, searchString='', searchLang=None, creator=targetForm.creator.data,
                                       targetType='User',
                                       description=targetForm.description.data, subject=targetForm.subject.data,
                                       status=targetForm.status.data, lastCrawl=None, totalTweets=0,
                                       added=datetime.now(), woeid=None, index=targetForm.index.data,
                                       mediaHarvest=targetForm.mediaHarvest.data,url_harvest=targetForm.urlHarvest.data,
                                       schedule=None, scheduleInterval=None, scheduleText = None,
                                       ia_uri=None,ia_cap_count=0,ia_cap_date=None)

            addLog = models.CRAWLLOG(tag_title=targetForm.title.data, event_start=datetime.now(), event_text='Target added',event_description=None)
            #addTarget.logs.append(addLog)
            #db.session.add(addTarget)
            object.tags.append(addTarget)
            db.session.commit()
            db.session.close()
            flash(u'Record saved! ', 'success')
        except IntegrityError:
            flash(u'Collection name is already in use!  ', 'danger')
            db.session.rollback()
        return redirect(url_for('collectionDetail', id=id, page=1))


    if request.method == 'POST' and searchApiForm.validate_on_submit():
        try:
            addTarget = models.TWITTER(title=searchApiForm.title.data, searchString=searchApiForm.searchString.data,searchLang=searchApiForm.searchLang.data,
                                       creator=searchApiForm.creator.data,
                                       targetType='Search',
                                       description=searchApiForm.description.data, subject=searchApiForm.subject.data,
                                       status=searchApiForm.status.data, lastCrawl=None, totalTweets=0,
                                       added=datetime.now(), woeid=None, index=searchApiForm.index.data,
                                       mediaHarvest=searchApiForm.mediaHarvest.data,url_harvest=searchApiForm.urlHarvest.data,
                                       schedule=None, scheduleInterval=None, scheduleText = None,
                                       ia_uri=None,ia_cap_count=0,ia_cap_date=None)

            addLog = models.CRAWLLOG(tag_title=targetForm.title.data, event_start=datetime.now(),
                                     event_text='Target added',event_description=None)
            # addTarget.logs.append(addLog)
            # db.session.add(addTarget)
            object.tags.append(addTarget)
            db.session.commit()
            db.session.close()

            flash(u'Record saved! ', 'success')
        except IntegrityError:
            flash(u'Collection name is already in use!  ', 'danger')
            db.session.rollback()
        return redirect(url_for('collectionDetail', id=id, page=1))

    return render_template("collectiondetail.html",  object = object, collectionForm=collectionForm, targetForm=targetForm,searchApiForm=searchApiForm, schedForm = schedForm, linkedTargets=linkedTargets, EXPORTS=EXPORTS)

'''
Route to add collection <--> target association
'''
@app.route('/addassociation/<id>/<target>', methods=['GET','POST'])
@auth.login_required
def addCollectionAssociation(id, target):
    object =  db.session.query(models.COLLECTION).get(id)
    linkedTarget = db.session.query(models.TWITTER).filter(models.TWITTER.row_id == target).one()
    object.tags.append(linkedTarget)
    db.session.commit()

    return redirect(url_for('collectionDetail', id=id, page=1))

"""Route to delete indexed tweets"""
@app.route('/deleteindextweets/<id>')
def dltIndexTweets(id):
    eq.enqueue(deleteindextweets, id)
    flash(u'Removing indexed tweets for target!', 'success')
    return redirect(request.referrer)




'''
Route to remove twitter-target
'''
@app.route('/removetwittertarget/<id>', methods=['GET','POST'])
@auth.login_required
def removeTwitterTarget(id):
    deleteindextweets(id)
    TWITTER = models.TWITTER.query.get_or_404(id)
    shutil.rmtree(os.path.join(ARCHIVE_BASEDIR,TWITTER.targetType,TWITTER.title[0],TWITTER.title), ignore_errors=True)
    db.session.delete(TWITTER)
    db.session.commit()
    db.session.close()
    if TWITTER.targetType == 'Search':
        return redirect('/twittersearchtargets/1')
    else:
        return redirect('/twittertargets/1')
'''
Route to reactivate twitter-target
'''
@app.route('/reactivatetwittertarget/<id>', methods=['GET','POST'])
@auth.login_required
def reactivateTwitterTarget(id):
    object = models.TWITTER.query.get_or_404(id)
    object.status = '1'
    db.session.commit()
    if object.targetType == 'Search':
        return redirect('/twittersearchtargetsclosed/1')
    else:
        return redirect('/twittertargetsclosed/1')

'''
Route to close twitter-target
'''
@app.route('/closetwittertarget/<id>', methods=['GET','POST'])
@auth.login_required
def closeTwitterTarget(id):
    object = models.TWITTER.query.get_or_404(id)
    object.status = '0'
    db.session.commit()
    if object.targetType == 'Search':
        return redirect('/twittersearchtargets/1')
    else:
        return redirect('/twittertargets/1')

'''
Route to remove collection
'''
@app.route('/removecollection/<id>', methods=['GET','POST'])
@auth.login_required
def removeCollection(id):
    object = models.COLLECTION.query.get_or_404(id)
    db.session.delete(object)
    db.session.commit()
    db.session.close()

    return redirect('/collections/1')

'''
Route to remove collection <--> target association
'''

@app.route('/removeassociation/<id>/<target>', methods=['GET','POST'])
@auth.login_required
def removeCollectionAssociation(id, target):
    object =  db.session.query(models.COLLECTION).get(id)
    linkedTarget = db.session.query(models.TWITTER).filter(models.TWITTER.row_id == target).one()
    object.tags.remove(linkedTarget)
    db.session.commit()
    return redirect(request.referrer)



'''
Route to call twarc-archive
'''
@app.route('/starttwittercrawl/<id>', methods=['GET','POST'])
@auth.login_required
def startTwitterCrawl(id):
    with app.app_context():

        last_crawl = models.TWITTER.query.get(id)
        last_crawl.lastCrawl = datetime.utcnow()
        db.session.commit()
        db.session.close()
        flash(u'Archiving started!',  'success')
        object = models.TWITTER.query.get_or_404(id)
        q.enqueue(twittercrawl, id, timeout=86400)
        return redirect(request.referrer)


"""Route to monitor if job is in queue"""
@app.route('/_qmonitor', methods=['GET', 'POST'])
def qmonitor():

    return jsonify(qlen=len(q),eqlen=len(eq))

"""Route to monitor if job is in queue"""
@app.route('/_emonitor', methods=['GET', 'POST'])
def emonitor():
    json_list = [i.serialize for i in models.CRAWLLOG.query.order_by(models.CRAWLLOG.row_id.desc()).limit(10).all()]

    return jsonify(json_list=json_list)

'''
Route to call collection twarc-archive
'''

@app.route('/startcollectioncrawl/<id>', methods=['GET','POST'])
@auth.login_required
def startCollectionCrawl(id):
    with app.app_context():
        #jobId = str(uuid.uuid4())
        COLLECTION = object = models.COLLECTION.query.get_or_404(id)
        COLLECTION.lastCrawl = datetime.now()
        db.session.commit()
        db.session.close()
        flash(u'Archiving started!', 'success')
        eq.enqueue(startScheduleCollectionCrawl, id, timeout=86400)

        return redirect(url_for('collectionDetail', id=id, page=1))

'''
Route to call followers
'''
@app.route('/followers/<id>', methods=['GET','POST'])
@auth.login_required
def followers(id):

    eq.enqueue(Followers, id, timeout=86400)
    flash(u'Getting followers, please refresh page!', 'success')
    return redirect(request.referrer)


'''
Route to call followers
'''
@app.route('/bagit/<id>', methods=['GET','POST'])
@auth.login_required
def bagit(id):
    eq.enqueue(bagger, id, timeout=86400)
    flash(u'Bagging!', 'success')
    return redirect(request.referrer)

'''
Route to push tweet to IA
'''
@app.route('/push/<id>/<type>', methods=['GET','POST'])
@auth.login_required
def IA_Push(id, type):
    if type == 'timeline':
            eq.enqueue(pushAccount, id, timeout=2000)
            flash(u'Pushing Account to Internet Archive', 'success')
    else:
        eq.enqueue(push, id, timeout=2000)
        flash(u'Pushing tweet to Internet Archive', 'success')
    return redirect(request.referrer)
'''
Route to call hashtag report
'''
@app.route('/hash/<id>', methods=['GET','POST'])
@auth.login_required
def hash(id):
    if '/twittertargets' in request.referrer:
        eq.enqueue(hashTags, id, timeout=86400)
        flash(u'Getting hashtags, please refresh page!', 'success')

    elif '/collectiondetail' in request.referrer:
        eq.enqueue(hashTagsCollection, id, timeout=86400)

    else:
        flash(u'Ooops something went wrong!', 'danger')

    return redirect(request.referrer)

'''
Route to call hash
'''
@app.route('/topuser/<id>', methods=['GET','POST'])
@auth.login_required
def top_users(id):
    if '/twittertargets' in request.referrer:
        eq.enqueue(topUsers, id, timeout=86400)
        flash(u'Getting top users, please refresh page!', 'success')

    elif '/collectiondetail' in request.referrer:
        eq.enqueue(topUsersCollection, id, timeout=86400)

    else:
        flash(u'Ooops something went wrong!', 'danger')

    return redirect(request.referrer)

'''
Route to call dehydrate report 
'''
@app.route('/dehydrate/<id>', methods=['GET','POST'])
@auth.login_required
def dehydrate(id):
    if '/twittertargets' in request.referrer:
        eq.enqueue(dehydrateUserSearch, id, timeout=86400)
        flash(u'Dehydrating, please refresh page!', 'success')

    elif '/collectiondetail' in request.referrer:
        eq.enqueue(dehydrateCollection, id, timeout=86400)
        flash(u'Dehydrating, please refresh page!', 'success')

    else:
        flash(u'Ooops something went wrong!', 'danger')

    return redirect(request.referrer)

'''
Route to call urls report 
'''
@app.route('/urls/<id>', methods=['GET','POST'])
@auth.login_required
def urls(id):
    if '/twittertargets' in request.referrer:
        eq.enqueue(urlsUserSearch, id, timeout=86400)
        flash(u'Extracting urls, please refresh page!', 'success')

    elif '/collectiondetail' in request.referrer:
        eq.enqueue(urlsCollection, id, timeout=86400)
        flash(u'Extracting urls, please refresh page!', 'success')

    else:
        flash(u'Ooops something went wrong!', 'danger')

    return redirect(request.referrer)

'''
Enables Functionality to create Heritrix crawler-beans
'''
@app.route('/catalogtemplate/<id>', methods=['GET','POST'])
@auth.login_required
def catalogTemplate(id):
    export_uuid = uuid.uuid4()
    object = models.TWITTER.query.get_or_404(id)
    outputCrawlerBeans = render_template('crawler-beans.cxml', object=object)
    with open(os.path.join(EXPORTS_BASEDIR, '{}_dataset_UUID_{}.yml'.format(q.title, export_uuid)), 'w+') as f:
        f.write(outputCrawlerBeans)
    return 'yay'

'''
Route to call wordCloud
'''
@app.route('/wordcloud/<id>', methods=['GET','POST'])
@auth.login_required
def wordc(id):
    if '/twittertargets' in request.referrer:
        eq.enqueue(wordCloud, id, timeout=86400)
        flash(u'Generating wordcloud, please refresh page!', 'success')

    elif '/collectiondetail' in request.referrer:
        eq.enqueue(wordCloudCollection, id, timeout=86400)
        flash(u'Generating wordcloud, please refresh page!', 'success')

    else:
        flash(u'Ooops something went wrong!', 'danger')

    return redirect(request.referrer)
'''
Route to call CSV
'''
@app.route('/t_csv/<id>', methods=['GET','POST'])
@auth.login_required
def t_csv(id):
    if '/twittertargets' in request.referrer:
        eq.enqueue(csvUserSearch, id, timeout=86400)
        flash(u'Generating CSV, please refresh page!', 'success')

    elif '/collectiondetail' in request.referrer:
        eq.enqueue(csvCollection, id, timeout=86400)
        flash(u'Generating CSV, please refresh page!', 'success')

    else:
        flash(u'Ooops something went wrong!', 'danger')


    return redirect(request.referrer)


'''
Route to send exports  
'''
@app.route('/export/<filename>')
@auth.login_required
def export(filename):
    return send_from_directory(app.config['EXPORTS_BASEDIR'],
                               filename)
'''
Route to send backups  
'''
@app.route('/backups/<filename>')
@auth.login_required
def backup_dir(filename):
    return send_from_directory(app.config['BACKUP_BASEDIR'],
                               filename)

'''
Route to send from archive dir
'''
@app.route('/archivedir/<id>/<filename>')
@auth.login_required
def archivedir(id,filename):
    TWITTER = models.TWITTER.query.get_or_404(id)
    return send_from_directory(os.path.join(ARCHIVE_BASEDIR,TWITTER.targetType,TWITTER.title[0],TWITTER.title, filename))

'''
Route to delete backups 
'''
@app.route('/deletebackup/<filename>')
@auth.login_required
def deletebackup(filename):
    try:
        os.remove(os.path.join(app.config['BACKUP_BASEDIR'],filename))
        flash(u'backup file deleted!', 'success')
    except:
        flash(u'Sorry could not delete backup', 'danger')
    return redirect(request.referrer)

'''
Route to delete exports  
'''
@app.route('/deleteexport/<filename>')
@auth.login_required
def deleteexport(filename):
    try:
        os.remove(os.path.join(app.config['EXPORTS_BASEDIR'],filename))
        flash(u'Export file deleted!', 'success')
    except:
        flash(u'The file seems to be missing! But the DB-record was deleted', 'danger')
    export = db.session.query(models.EXPORTS).filter(models.EXPORTS.url == filename).one()
    db.session.delete(export)
    db.session.commit()
    db.session.close()
    return redirect(request.referrer)

'''CREDENIALS SETTINGS ROUTE'''
@app.route('/credentials', methods=['GET', 'POST'])
@auth.login_required
def credentials():
    credentialForm = credForm()
    passForm = passwordForm()
    credentials = models.CREDENTIALS.query.all()

    if request.method == 'POST' and passForm.validate_on_submit():
        USERS = models.USERS.query.filter(models.USERS.row_id == 1).first()
        USERS.passw = generate_password_hash(passForm.password.data)
        db.session.commit()
        flash(u'Admin password changed', 'success')
        return redirect(request.referrer)

    if request.method == 'POST' and credentialForm.validate_on_submit():
        addCred = models.CREDENTIALS(name=credentialForm.name.data,consumer_key=credentialForm.consumer_key.data,
                                     consumer_secret=credentialForm.consumer_secret.data,access_token=credentialForm.access_token.data,
                                     access_secret=credentialForm.access_secret.data)
        db.session.add(addCred)
        db.session.commit()
        flash(u'Added Twitter Credentials'.format(credentialForm.name.data), 'success')
        return redirect(request.referrer)

    return render_template("credentials_settings.html", credentials=credentials, credentialForm=credentialForm, passForm=passForm)

'''VOCABS SETTINGS ROUTE'''
@app.route('/vocabs', methods=['GET', 'POST'])
@auth.login_required
def vocabs():
    stopWords = models.STOPWORDS.query.all()
    stopForm = stopWordsForm()
    typeForm = collectionTypeForm()
    langForm = langCodeForm()
    silencedTrends = models.TWITTER_TRENDS.query.filter(models.TWITTER_TRENDS.silence == True).order_by(models.TWITTER_TRENDS.name.asc()).all()
    collectionTypes = models.VOCABS.query.filter(models.VOCABS.use == 'collectionType').order_by(models.VOCABS.term.asc()).all()
    langcodes = models.VOCABS.query.filter(models.VOCABS.use == 'langcode').order_by(models.VOCABS.term.asc()).all()

    if request.method == 'POST' and stopForm.validate_on_submit():

        add_stop_words = models.STOPWORDS(stop_word=stopForm.stopWord.data, lang=None)
        db.session.add(add_stop_words)
        db.session.commit()
        flash(u'{} was added to Stop word list!'.format(stopForm.stopWord.data), 'success')
        return redirect(request.referrer)
    return render_template("vocab_settings.html", collectionTypes=collectionTypes, stopWords=stopWords,
                           stopForm=stopForm,  typeForm=typeForm, langForm=langForm, langcodes=langcodes,silencedTrends = silencedTrends)


'''DB / STORAGE SETTINGS ROUTE'''
@app.route('/dbstorage', methods=['GET', 'POST'])
@auth.login_required
def dbstorage():
    dbExports = models.EXPORTS.query.filter(models.EXPORTS.type=='db').all()
    diskList = []
    for mountPoint in psutil.disk_partitions():
        x = dict(p=psutil.disk_usage(mountPoint[1])[3], n=mountPoint[0], m=mountPoint[1],
                 f=str(psutil.disk_usage(mountPoint[1])[2] / (1024.0 ** 3)))
        diskList.append(x)

    fileList = []
    try:
        for filename in os.listdir(os.path.join(BACKUP_BASEDIR)):
            if filename.endswith(".sql"):
                try:
                    mtime = os.path.getmtime(os.path.join(BACKUP_BASEDIR, filename))
                except OSError:
                    mtime = 0
                last_modified_date = datetime.fromtimestamp(mtime)
                y = dict(fname=filename,
                         fsize=humansize(os.path.getsize(os.path.join(BACKUP_BASEDIR, filename))),
                         fdate=last_modified_date)
                fileList.append(y)
    except:
        pass
    return render_template("db_storage_settings.html",diskList=diskList, dbExports=dbExports, fileList=fileList)

'''DB / STORAGE SETTINGS ROUTE'''
@app.route('/workersqueues', methods=['GET', 'POST'])
@auth.login_required
def workers_queues():
    workers = Worker.all(connection=Redis())
    return render_template("workers_queues_settings.html",workers=workers,qlen=len(q),intqlen=len(eq))



'''Route to remove credential'''
@app.route('/removecredential/<id>', methods=['GET', 'POST'])
@auth.login_required
def removecredential(id):
    object =  db.session.query(models.CREDENTIALS).get(id)
    db.session.delete(object)
    db.session.commit()
    flash(u'Credential named {} was deleted!'.format(object.name), 'success')
    return redirect(request.referrer)

'''Route to remove stop word'''
@app.route('/removestopword/<id>', methods=['GET', 'POST'])
@auth.login_required
def removestopword(id):
    object = object =  db.session.query(models.STOPWORDS).get(id)
    db.session.delete(object)
    db.session.commit()
    flash(u'{} was removed from stop word list!'.format(object.stop_word), 'success')
    return redirect(request.referrer)


# Function to control allowed file extensions
ALLOWED_EXTENSIONS = set(['txt'])
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploadstopwords', methods=['GET','POST'])
@auth.login_required
def uploadStopWords():

    if request.method == 'POST':
        file = request.files['file']
        if 'file' not in request.files:
            flash(u'No file part','danger')
            return redirect(request.referrer)
        if file.filename == '':
            flash(u'No selected file','danger')
            return redirect(request.referrer)
        if not allowed_file(file.filename):
            flash(u'Only txt-files allowed', 'danger')
            return redirect(request.referrer)

        if file and allowed_file(file.filename):
            lineCount = 0
            for line in file.readlines():
                lineCount = lineCount + 1
                stopWord = line.decode('utf-8').replace('\n','')
                addUrl = models.STOPWORDS(stop_word=stopWord, lang=None)
                db.session.add(addUrl)

        db.session.commit()
        flash(u'{} stop words added!'.format(lineCount), 'success')
        return redirect(request.referrer)


@auth.login_required
@app.route('/deleteindex', methods=['GET','POST'])
def deleteIndex():
    eq.enqueue(delIndex)
    return redirect(request.referrer)

@auth.login_required
@app.route('/vaccum', methods=['GET','POST'])
def vaccum():
    eq.enqueue(vac)
    return redirect(request.referrer)

@auth.login_required
@app.route('/backup_db', methods=['GET','POST'])
def backupDB():
    eq.enqueue(backup_db)
    flash(u'Backing up database', 'success')
    return redirect(request.referrer)

@auth.login_required
@app.route('/reboot', methods=['GET','POST'])
def reboot():
    if request.method == 'POST':
        cmd = ["reboot", "now"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             stdin=subprocess.PIPE)
        out, err = p.communicate()
        return out
    else:
        return redirect(url_for('index'))

@auth.login_required
@app.route('/shutdown', methods=['GET','POST'])
def shutdown():
    if request.method == 'POST':
        cmd = ["shutdown","-h","now"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             stdin=subprocess.PIPE)
        out, err = p.communicate()
        return out
    else:
        return redirect(url_for('index'))

@auth.login_required
@app.route('/clearqueue/<type>', methods=['GET','POST'])
def clearQueue(type):
    if type == 'internal':
        eq.empty()

    elif type == 'archive':
        q.empty()

    return redirect(request.referrer)

@auth.login_required
@app.route('/dropSchedule/<id>', methods=['GET','POST'])
def dropSchedule(id):
    COLLECTION = models.COLLECTION.query.get_or_404(id)
    scheduler.cancel(COLLECTION.schedule)
    COLLECTION.scheduleInterval = None
    COLLECTION.schedule = None
    COLLECTION.scheduleText = None
    COLLECTION.nextRun = None
    db.session.commit()

    return redirect(request.referrer)