#!/usr/bin/env python
# -*- coding: utf-8 -*-
from app import app, render_template, request,db, url_for, redirect,flash,Response,jsonify, send_from_directory
from app import models
from .forms import twitterTargetForm, SearchForm, twitterCollectionForm, collectionAddForm, twitterTrendForm, stopWordsForm, scheduleForm,SCHEDULE_CHOICES
from sqlalchemy.exc import IntegrityError
from .twarcUIarchive import twittercrawl
from .twitterTrends import getTrends
from .getFollowers import Followers
from .hashtags import hashTags, hashTagsCollection
from .topusers import topUsers, topUsersCollection
from .dehydrate import dehydrateUserSearch,dehydrateCollection
from .wordcloud import wordCloud, wordCloudCollection
from .urls import urlsUserSearch, urlsCollection
from .scheduleCollection import startScheduleCollectionCrawl
from config import POSTS_PER_PAGE, REDIS_DB, MAP_VIEW,MAP_ZOOM,TARGETS_PER_PAGE,EXPORTS_BASEDIR,ARCHIVE_BASEDIR, TREND_UPDATE
from datetime import datetime, timedelta
from redis import Redis
from rq import Queue
from rq.worker import Worker
from rq_scheduler import Scheduler
import os
import psutil
import uuid

q = Queue(connection=Redis())
eq = Queue('internal',connection=Redis())
scheduler = Scheduler(connection=Redis())
@app.before_first_request
def before_first_request():
    COLLECTIONS = models.COLLECTION.query.all()

    for collection in COLLECTIONS:
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
        search_form = SearchForm()



'''INDEX ROUTE'''
@app.route('/')
@app.route('/index', methods=['GET', 'POST'])
def index():
    twitterUserCount = models.TWITTER.query.filter(models.TWITTER.status == '1').filter(models.TWITTER.targetType=='User').count()
    twitterSearchCount = models.TWITTER.query.filter(models.TWITTER.status == '1').filter(models.TWITTER.targetType == 'Search').count()
    collectionCount = models.COLLECTION.query.filter(models.COLLECTION.status=='1').count()
    trendsCount = db.session.query(models.TRENDS_LOC).count()
    CRAWLLOG = models.CRAWLLOG.query.order_by(models.CRAWLLOG.row_id.desc()).limit(10).all()
    form = SearchForm()
    if request.method == 'POST':
        return redirect((url_for('search_results', form=form, query=form.search.data)))

    return render_template("index.html", twitterUserCount=twitterUserCount, twitterSearchCount=twitterSearchCount, collectionCount=collectionCount,trendsCount=trendsCount, CRAWLLOG=CRAWLLOG,  qlen=len(q), form=form)


'''SEARCH'''
@app.route('/search', methods=['GET', 'POST'])
def search():
    form =SearchForm()
    if request.method == 'POST':
        return redirect((url_for('search_results', form=form, query=form.search.data, page=1)))
    return render_template("search.html", form=form)


'''SEARCH RESULTS'''
@app.route('/search/<query>/<int:page>', methods=['GET', 'POST'])
def search_results(query,page=1):
    form = SearchForm()
    results = models.SEARCH.query.filter(models.SEARCH.text.like(u'%{}%'.format(query))).paginate(page, POSTS_PER_PAGE, False)
    return render_template('search.html', query=query, results=results,form=form)

'''
TWITTER
'''

'''USER-TIMELINES'''
@app.route('/twittertargets/<int:page>', methods=['GET', 'POST'])
def twittertargets(page=1):
    TWITTER = models.TWITTER.query.filter(models.TWITTER.targetType=='User').filter(models.TWITTER.status==1).order_by(models.TWITTER.title).paginate(page, TARGETS_PER_PAGE,False)
    form = twitterTargetForm(prefix='form')

    if request.method == 'POST'and form.validate_on_submit():

        try:


            addTarget = models.TWITTER(title=form.title.data, searchString='', creator=form.creator.data, targetType='User',
                                       description=form.description.data, subject=form.subject.data, status=form.status.data,lastCrawl=None, totalTweets=0,
                                       added=datetime.now(), woeid=None, index=form.index.data, schedule=None, scheduleInterval=None, scheduleText = None)

            addLog = models.CRAWLLOG(tag_title=form.title.data,event_start=datetime.now(), event_text='ADDED TO DB')
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
def twittertargetsclosed(page=1):
    TWITTER = models.TWITTER.query.filter(models.TWITTER.targetType=='User').filter(models.TWITTER.status==0).order_by(models.TWITTER.title).paginate(page, TARGETS_PER_PAGE,False)
    form = twitterTargetForm(prefix='form')

    if request.method == 'POST'and form.validate_on_submit():

        try:


            addTarget = models.TWITTER(title=form.title.data, searchString='', creator=form.creator.data, targetType='User',
                                       description=form.description.data, subject=form.subject.data, status=form.status.data,lastCrawl=None, totalTweets=0,
                                       added=datetime.now(), woeid=None, index=form.index.data, schedule=None, scheduleInterval=None, scheduleText = None)

            addLog = models.CRAWLLOG(tag_title=form.title.data,event_start=datetime.now(), event_text='ADDED TO DB')
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
def twittertrends():
    filterTime = datetime.utcnow() - timedelta(minutes=60)
    loc = models.TRENDS_LOC.query.all()
    trend = models.TWITTER_TRENDS.query.filter(models.TWITTER_TRENDS.collected > filterTime).all()
    trendAll = models.TWITTER_TRENDS.query.order_by(models.TWITTER_TRENDS.collected.desc()).all()
    trendForm = twitterTrendForm(prefix='trendform')
    form = twitterTargetForm(prefix='form')
    schedForm = scheduleForm(prefix='schedForm')



    if request.method == 'POST' and trendForm.validate_on_submit():
        addloc = models.TRENDS_LOC(name=None,loc=trendForm.geoloc.data,schedule=None, scheduleInterval=None, scheduleText=None)
        db.session.add(addloc)
        db.session.commit()
        eq.enqueue(getTrends)
        flash(u'Trend location added!', 'success')
        return redirect((url_for('twittertrends')))
    if request.method == 'POST' and not trendForm.validate_on_submit():
        flash(u'Not a valid location!', 'danger')
        return redirect((url_for('twittertrends')))

    return render_template("trends.html", loc=loc, trend=trend, trendForm=trendForm, form=form, trendAll=trendAll, MAP_VIEW = MAP_VIEW, MAP_ZOOM=MAP_ZOOM)



"""Route to add Trend to Search"""
@app.route('/addtwittertrend/<id>', methods=['GET', 'POST'])
def addtwittertrend(id):
    trendAll = models.TWITTER_TRENDS.query.all()
    twitterTargets = models.TWITTER.query.all()
    if request.method == 'POST':
        addTarget = models.TWITTER(title=id, searchString=id,
                                   creator='', targetType='Search',
                                   description='', subject='',
                                   status='1', lastCrawl=None, totalTweets=0,
                                   added=datetime.now(), woeid=None, index='0', schedule=None, scheduleInterval=None, scheduleText = None)

        addLog = models.CRAWLLOG(tag_title=id, event_start=datetime.now(), event_text='Added to database')
        addLog2 = models.CRAWLLOG(tag_title=id, event_start=datetime.now(), event_text='Manually added from Trend monitoring')
        for t in trendAll:
            if t.name == id:
                t.saved= True

        addTarget.logs.append(addLog)
        addTarget.logs.append(addLog2)
        db.session.add(addTarget)
        db.session.commit()
        db.session.close()
        return redirect((url_for('twittertrends')))


"""Route to clear Trends"""
@app.route('/cleartwittertrend/<id>', methods=['GET', 'POST'])
def cleartwittertrend(id):
    trendAll = models.TRENDS_LOC.query.filter(models.TRENDS_LOC.row_id==id).all()
    print (request.url_rule)
    for t in trendAll:
        for trend in t.trends:
            if trend.saved == False:
                db.session.delete(trend)
    db.session.commit()
    return redirect((url_for('twittertrends')))


"""Route to delete Trend Location"""
@app.route('/deletetrendlocation/<id>', methods=['GET', 'POST'])
def deleteTrendLocation(id):
    trendLocation = models.TRENDS_LOC.query.filter(models.TRENDS_LOC.row_id==id).first()
    db.session.delete(trendLocation)
    db.session.commit()
    return redirect((url_for('twittertrends')))

"""Route to remove Trend from Search"""
@app.route('/removetwittertrend/<id>', methods=['GET', 'POST'])
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
def refreshtwittertrend():
    eq.enqueue(getTrends)
    return redirect((url_for('twittertrends')))


'''API-SEARCH-TARGETS'''
@app.route('/twittersearchtargets/<int:page>', methods=['GET', 'POST'])
def twittersearchtargets(page=1):

    TWITTER = models.TWITTER.query.filter(models.TWITTER.targetType == 'Search').filter(models.TWITTER.status==1).order_by(models.TWITTER.title).paginate(page, TARGETS_PER_PAGE, False)
    templateType = "Search"
    openClosed = "Open"
    form = twitterTargetForm(prefix='form')
    if request.method == 'POST'and form.validate_on_submit():
        try:
            addTarget = models.TWITTER(title=form.title.data, searchString=form.searchString.data, creator=form.creator.data, targetType='Search',
                                       description=form.description.data, subject=form.subject.data,
                                       status=form.status.data, lastCrawl=None, totalTweets=0,
                                       added=datetime.now(), woeid=None, index=form.index.data, schedule=None, scheduleInterval=None, scheduleText = None)
            addLog = models.CRAWLLOG(tag_title=form.title.data, event_start=datetime.now(), event_text='ADDED TO DB')
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
def twittersearchtargetsclosed(page=1):
    TWITTER = models.TWITTER.query.filter(models.TWITTER.targetType == 'Search').filter(models.TWITTER.status==0).order_by(models.TWITTER.title).paginate(page, TARGETS_PER_PAGE, False)
    templateType = "Search"
    form = twitterTargetForm(prefix='form')
    if request.method == 'POST'and form.validate_on_submit():
        try:
            addTarget = models.TWITTER(title=form.title.data, searchString=form.searchString.data, creator=form.creator.data, targetType='Search',
                                       description=form.description.data, subject=form.subject.data,
                                       status=form.status.data, lastCrawl=None, totalTweets=0,
                                       added=datetime.now(), woeid=None, index=form.index.data, schedule=None, scheduleInterval=None, scheduleText = None)
            addLog = models.CRAWLLOG(tag_title=form.title.data, event_start=datetime.now(), event_text='ADDED TO DB')
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
def collections(page=1):
    COLLECTIONS = models.COLLECTION.query.filter(models.COLLECTION.status == '1').order_by(models.COLLECTION.title).paginate(page, TARGETS_PER_PAGE, False)

    collectionForm = twitterCollectionForm(prefix='collectionForm')
    if request.method == 'POST' and collectionForm.validate_on_submit():
        try:
            addTarget = models.COLLECTION(title=collectionForm.title.data, curator=collectionForm.curator.data,
                                       collectionType=collectionForm.collectionType.data,
                                       description=collectionForm.description.data, subject=collectionForm.subject.data,
                                       status=collectionForm.status.data, inclDateStart=collectionForm.inclDateStart.data,
                                       inclDateEnd=collectionForm.inclDateStart.data, lastCrawl=None,
                                       totalTweets=0, added=datetime.now(),schedule=None, scheduleInterval=None, scheduleText = None)

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

'''
Route to call Schedule
'''
@app.route('/schedule/<id>', methods=['GET','POST'])
def schedule(id):
    jobId = str(uuid.uuid4())
    if '/twittertargets' in request.referrer:

        flash(u'Scheduled Target!', 'success')

    elif '/collectiondetail' in request.referrer:
        object = models.COLLECTION.query.filter(models.COLLECTION.row_id == id).first()
        if object.schedule:
            scheduler.cancel(object.schedule)
        object.schedule = jobId
        scheduler.schedule(
            scheduled_time=datetime.utcnow(),  # Time for first execution, in UTC timezone
            func=startScheduleCollectionCrawl,  # Function to be queued
            args=[id],
            interval=900,  # Time before the function is called again, in seconds
            repeat=None, # Repeat this number of times (None means repeat forever)
            id=jobId
        )

        db.session.commit()
        flash(u'Scheduled Collection', 'success')

    else:
        flash(u'Ooops something went wrong!', 'danger')

    return redirect(request.referrer)


'''Route to view archived user tweets '''
@app.route('/usertweets/<id>/<int:page>', methods=['GET', 'POST'])
def userlist(id,page=1):
    id=id
    print (id)
    results = models.SEARCH.query.filter(models.SEARCH.username==id).order_by(models.SEARCH.created_at.desc()).paginate(page, POSTS_PER_PAGE, False)
    twitterTarget = models.TWITTER.query.filter(models.TWITTER.title == id).first()
    form = twitterTargetForm(prefix='form')
    if request.method == 'POST' and form.validate_on_submit():
        try:
            addTarget = models.TWITTER(title=form.title.data,searchString='' ,creator=form.creator.data, targetType='User',
                                       description=form.description.data, subject=form.subject.data,
                                       status=form.status.data, lastCrawl=None, totalTweets=0,
                                       added=datetime.now(), woeid=None, index=form.index.data, schedule=None, scheduleInterval=None , scheduleText = None)

            addLog = models.CRAWLLOG(tag_title=form.title.data, event_start=datetime.now(), event_text='ADDED TO DB')
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

'''Route to view archived user tweets from twitter searches '''
@app.route('/searchtweets/<id>/<int:page>', methods=['GET', 'POST'])
def searchlist(id,page=1):
    id=id
    results = models.SEARCH.query.filter(models.SEARCH.source==id).order_by(models.SEARCH.created_at.desc()).paginate(page, POSTS_PER_PAGE, False)
    twitterTarget = models.TWITTER.query.filter(models.TWITTER.row_id == id).first()
    form = twitterTargetForm(prefix='form')
    if request.method == 'POST' and form.validate_on_submit():
        try:
            addTarget = models.TWITTER(title=form.title.data,searchString='' ,creator=form.creator.data, targetType='User',
                                       description=form.description.data, subject=form.subject.data,
                                       status=form.status.data, lastCrawl=None, totalTweets=0,
                                       added=datetime.now(), woeid=None, index=form.index.data, schedule=None, scheduleInterval=None , scheduleText = None)
            addLog = models.CRAWLLOG(tag_title=form.title.data, event_start=datetime.now(), event_text='ADDED TO DB')
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
def twittertargetDetail(id):

    TWITTER = models.TWITTER.query.filter(models.TWITTER.row_id == id).first()
    object = models.TWITTER.query.get_or_404(id)
    CRAWLLOG = models.CRAWLLOG.query.order_by(models.CRAWLLOG.event_start.desc()).filter(models.CRAWLLOG.tag_id==id).limit(1)
    EXPORTS = models.EXPORTS.query.order_by(models.EXPORTS.row_id.desc()).filter(models.EXPORTS.twitter_id==id)
    form = twitterTargetForm(prefix='form',obj=object)
    assForm = collectionAddForm(prefix="assForm")
    linkedCollections = models.TWITTER.query. \
        filter(models.TWITTER.row_id == id). \
        first(). \
        tags
    l = []


    if request.method == 'POST' and assForm.validate_on_submit():
        object.tags.append(assForm.assoc.data)
        db.session.commit()
        return redirect(url_for('twittertargetDetail', id=id))


    if request.method == 'POST' and form.validate_on_submit():
        try:
            form.populate_obj(object)
            addLog = models.CRAWLLOG(tag_title=form.title.data, event_start=datetime.now(), event_text='DESCRIPTION ALTERED')
            object.logs.append(addLog)
            db.session.add(object)
            db.session.commit()
            db.session.close()
            flash(u'Record saved! ', 'success')
        except IntegrityError:
            flash(u'Twitter user account already in database ', 'danger')
            db.session.rollback()
        return redirect(url_for('twittertargetDetail',id=id))



    return render_template("twittertargetdetail.html", TWITTER=TWITTER, form=form, CRAWLLOG=CRAWLLOG, EXPORTS=EXPORTS, linkedCollections=linkedCollections, assForm=assForm, l=l)

'''Route to detail view of collections'''
@app.route('/collectiondetail/<id>/<int:page>', methods=['GET', 'POST'])
def collectionDetail(id, page=1):
    object = models.COLLECTION.query.get_or_404(id)
    #targets = models.TWITTER.query.all()
    EXPORTS = models.EXPORTS.query.order_by(models.EXPORTS.row_id.desc()).filter(models.EXPORTS.collection_id == id)
    #CRAWLLOG = models.CRAWLLOG.query.order_by(models.CRAWLLOG.row_id.desc()).filter(models.CRAWLLOG.tag_id==id)
    #TWITTER = models.TWITTER.query.filter(models.TWITTER.status == '1').filter(models.TWITTER.targetType == 'User').order_by(models.TWITTER.title).paginate(page, TARGETS_PER_PAGE, False)
    linkedTargets =  models.COLLECTION.query.filter(models.COLLECTION.row_id==id).first().tags.paginate(page, POSTS_PER_PAGE, False)


    collectionForm = twitterCollectionForm(prefix='collectionform',obj=object)
    targetForm = twitterTargetForm(prefix='targetform')
    searchApiForm = twitterTargetForm(prefix='searchapiform')
    schedForm = scheduleForm(prefix="schedForm")

    if request.method == 'POST' and schedForm.validate_on_submit():
        jobId = str(uuid.uuid4())
        if object.schedule:
            scheduler.cancel(object.schedule)
        object.schedule = jobId
        object.scheduleText = dict(SCHEDULE_CHOICES).get(schedForm.schedule.data)

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
            addTarget = models.TWITTER(title=targetForm.title.data, searchString='', creator=targetForm.creator.data,
                                       targetType='User',
                                       description=targetForm.description.data, subject=targetForm.subject.data,
                                       status=targetForm.status.data, lastCrawl=None, totalTweets=0,
                                       added=datetime.now(), woeid=None, index=targetForm.index.data, schedule=None, scheduleInterval=None, scheduleText = None)

            addLog = models.CRAWLLOG(tag_title=targetForm.title.data, event_start=datetime.now(), event_text='ADDED TO DB')
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
            addTarget = models.TWITTER(title=searchApiForm.title.data, searchString=searchApiForm.searchString.data,
                                       creator=searchApiForm.creator.data,
                                       targetType='Search',
                                       description=searchApiForm.description.data, subject=searchApiForm.subject.data,
                                       status=searchApiForm.status.data, lastCrawl=None, totalTweets=0,
                                       added=datetime.now(), woeid=None, index=searchApiForm.index.data,
                                       schedule=None, scheduleInterval=None, scheduleText = None)

            addLog = models.CRAWLLOG(tag_title=targetForm.title.data, event_start=datetime.now(),
                                     event_text='ADDED TO DB')
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
def addCollectionAssociation(id, target):
    object =  db.session.query(models.COLLECTION).get(id)
    linkedTarget = db.session.query(models.TWITTER).filter(models.TWITTER.row_id == target).one()
    object.tags.append(linkedTarget)
    db.session.commit()

    return redirect(url_for('collectionDetail', id=id, page=1))


'''
Route to remove twitter-target
'''
@app.route('/removetwittertarget/<id>', methods=['GET','POST'])
def removeTwitterTarget(id):
    object = models.TWITTER.query.get_or_404(id)
    db.session.delete(object)
    db.session.commit()
    db.session.close()
    if object.targetType == 'Search':
        return redirect('/twittersearchtargets/1')
    else:
        return redirect('/twittertargets/1')
'''
Route to reactivate twitter-target
'''
@app.route('/reactivatetwittertarget/<id>', methods=['GET','POST'])
def reactivateTwitterTarget(id):
    object = models.TWITTER.query.get_or_404(id)
    object.status = 1
    db.session.commit()
    if object.targetType == 'Search':
        return redirect('/twittersearchtargetsclosed/1')
    else:
        return redirect('/twittertargetsclosed/1')


'''
Route to remove collection
'''
@app.route('/removecollection/<id>', methods=['GET','POST'])
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
def startTwitterCrawl(id):
    with app.app_context():

        last_crawl = models.TWITTER.query.get(id)
        last_crawl.lastCrawl = datetime.now()
        db.session.commit()
        db.session.close()
        flash(u'Archiving started!',  'success')
        object = models.TWITTER.query.get_or_404(id)
        q.enqueue(twittercrawl, id, timeout=86400)
        return redirect(request.referrer)


"""Route to monitor if job is in queue"""
@app.route('/_qmonitor', methods=['GET', 'POST'])
def qmonitor():

    return jsonify(qlen=len(q))

'''
Route to call collection twarc-archive
'''

@app.route('/startcollectioncrawl/<id>', methods=['GET','POST'])
def startCollectionCrawl(id):
    with app.app_context():
        jobId = str(uuid.uuid4())
        flash(u'Archiving started!', 'success')
        eq.enqueue(startScheduleCollectionCrawl, id, timeout=86400)

        return redirect(url_for('collectionDetail', id=id, page=1))

'''
Route to call followers
'''
@app.route('/followers/<id>', methods=['GET','POST'])
def followers(id):

    eq.enqueue(Followers, id, timeout=86400)
    flash(u'Getting followers, please refresh page!', 'success')
    return redirect(request.referrer)

'''
Route to call hashtag report
'''
@app.route('/hash/<id>', methods=['GET','POST'])
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
Route to send exports  
'''
@app.route('/export/<filename>')
def export(filename):
    return send_from_directory(app.config['EXPORTS_BASEDIR'],
                               filename)

'''
Route to delete exports  
'''
@app.route('/deleteexport/<filename>')
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

'''SETTINGS ROUTE'''
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    stopWords = models.STOPWORDS.query.all()
    stopForm = stopWordsForm()

    if request.method == 'POST' and stopForm.validate_on_submit():

        add_stop_words = models.STOPWORDS(stop_word=stopForm.stopWord.data, lang=None)
        db.session.add(add_stop_words)
        db.session.commit()
        flash(u'{} was added to Stop word list!'.format(stopForm.stopWord.data), 'success')
        return redirect(request.referrer)
    diskList = []

    #DISKS
    for mountPoint in psutil.disk_partitions():
        x = dict(p=psutil.disk_usage(mountPoint[1])[3], n=mountPoint[0], f=str(psutil.disk_usage(mountPoint[1])[2]/ (1024.0 ** 3)))
        print (x)
        diskList.append(x)

    #REDIS
    workers = Worker.all(connection=Redis())


    return render_template("settings.html", stopWords = stopWords, stopForm = stopForm, diskList=diskList, workers=workers,qlen=len(q))


'''Route to remove stop word'''
@app.route('/removestopword/<id>', methods=['GET', 'POST'])
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





