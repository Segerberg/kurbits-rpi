#!/usr/bin/env python

from __future__ import print_function
import re
import json
from config import EXPORTS_BASEDIR,ARCHIVE_BASEDIR
import gzip
import uuid
import os
from datetime import datetime
from app import models,db

def wordCloud(id):
    try:
        from urllib import urlopen  # Python 2
    except ImportError:
        from urllib.request import urlopen  # Python 3

    MAX_WORDS = 200

    word_counts = {}
    stop_words = set([])
    q = models.STOPWORDS.query.all()
    for line in q:
        stop_words.add(line.stop_word)


    if not os.path.isdir(EXPORTS_BASEDIR):
        os.makedirs(EXPORTS_BASEDIR)
    q = models.TWITTER.query.filter(models.TWITTER.row_id == id).first()
    for filename in os.listdir(os.path.join(ARCHIVE_BASEDIR, q.title)):
        if filename.endswith(".gz"):
            for line in gzip.open(os.path.join(ARCHIVE_BASEDIR, q.title, filename)):

                tweet = json.loads(line.decode('utf-8'))


                for word in text(tweet).split(' '):
                    word = word.lower()
                    word = word.replace(".", "")
                    if len(word) < 3: continue
                    if len(word) > 15: continue
                    if word in stop_words: continue
                    if word[0] in ["@", "#"]: continue
                    if re.match('https?', word): continue
                    if word.startswith("rt"): continue
                    if not re.match('^[a-z]', word, re.IGNORECASE): continue
                    word_counts[word] = word_counts.get(word, 0) + 1

    sorted_words = list(word_counts.keys())
    sorted_words.sort(key = lambda x: word_counts[x], reverse=True)
    top_words = sorted_words[0:MAX_WORDS]

    words = []
    count_range = word_counts[top_words[0]] - word_counts[top_words[-1]]
    size_ratio = 100.0 / count_range
    for word in top_words:
        size = int(word_counts[word] * size_ratio) + 15
        words.append({
            "text": word,
            "size": size
        })

    wordcloud_js = urlopen('https://raw.githubusercontent.com/jasondavies/d3-cloud/master/build/d3.layout.cloud.js').read()

    output = """<!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <title>twarc wordcloud</title>
    <script src="http://d3js.org/d3.v3.min.js"></script>
    </head>
    <body>
    <script>

      // embed Jason Davies' d3-cloud since it's not available in a CDN
      %s

      var fill = d3.scale.category20();
      var words = %s

      d3.layout.cloud().size([800, 800])
          .words(words)
          .rotate(function() { return ~~(Math.random() * 2) * 90; })
          .font("Impact")
          .fontSize(function(d) { return d.size; })
          .on("end", draw)
          .start();

      function draw(words) {
        d3.select("body").append("svg")
            .attr("width", 1000)
            .attr("height", 1000)
          .append("g")
            .attr("transform", "translate(400,400)")
          .selectAll("text")
            .data(words)
          .enter().append("text")
            .style("font-size", function(d) { return d.size + "px"; })
            .style("font-family", "Impact")
            .style("fill", function(d, i) { return fill(i); })
            .attr("text-anchor", "middle")
            .attr("transform", function(d) {
              return "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")";
            })
            .text(function(d) { return d.text; });
      }
    </script>
    </body>
    </html>
    """ % (wordcloud_js.decode('utf8'), json.dumps(words, indent=2))


    export_uuid = uuid.uuid4()
    with open(os.path.join(EXPORTS_BASEDIR, '{}_wordcloud_UUID_{}.html'.format(q.title, export_uuid)), 'w+') as f:
            f.write(output)
    addExportRef = models.EXPORTS(url='{}_wordcloud_UUID_{}.html'.format(q.title, export_uuid),
                                  type='Wordcloud', exported=datetime.utcnow(), count=None)
    q.exports.append(addExportRef)
    db.session.commit()
    db.session.close()

def wordCloudCollection(id):
    try:
        from urllib import urlopen  # Python 2
    except ImportError:
        from urllib.request import urlopen  # Python 3

    MAX_WORDS = 200
    word_counts = {}
    stop_words = set([])

    q = models.STOPWORDS.query.all()
    for line in q:
        stop_words.add(line.stop_word)
        print (line.stop_word)

    if not os.path.isdir(EXPORTS_BASEDIR):
        os.makedirs(EXPORTS_BASEDIR)

    q = models.COLLECTION.query.filter(models.COLLECTION.row_id == id).first()
    dbDateStart = q.inclDateStart
    dbDateStop = q.inclDateEnd
    print (dbDateStart)
    print (dbDateStop)
    if dbDateStop == None:
        dbDateStop = datetime.max

    if dbDateStart == None:
        print ('dbdateStop')
        dbDateStart = datetime.min




    linkedTargets = models.COLLECTION.query. \
        filter(models.COLLECTION.row_id == id). \
        first(). \
        tags
    for target in linkedTargets:
        try:

            for filename in os.listdir(os.path.join(ARCHIVE_BASEDIR, target.title)):
                if filename.endswith(".gz"):
                    for line in gzip.open(os.path.join(ARCHIVE_BASEDIR, target.title, filename)):

                        tweet = json.loads(line.decode('utf-8'))
                        tweetDate = datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y')

                        if tweetDate > dbDateStart and tweetDate < dbDateStop:
                            print(tweetDate)

                            for word in text(tweet).split(' '):
                                word = word.lower()
                                word = word.replace(".", "")
                                if len(word) < 3: continue
                                if len(word) > 15: continue
                                if word in stop_words: continue
                                if word[0] in ["@", "#"]: continue
                                if re.match('https?', word): continue
                                if word.startswith("rt"): continue
                                if not re.match('^[a-z]', word, re.IGNORECASE): continue
                                word_counts[word] = word_counts.get(word, 0) + 1
        except:
            continue
        sorted_words = list(word_counts.keys())
        sorted_words.sort(key = lambda x: word_counts[x], reverse=True)
        top_words = sorted_words[0:MAX_WORDS]

        words = []
        count_range = word_counts[top_words[0]] - word_counts[top_words[-1]]
        size_ratio = 100.0 / count_range
        for word in top_words:
            size = int(word_counts[word] * size_ratio) + 15
            words.append({
                "text": word,
                "size": size
            })

    wordcloud_js = urlopen('https://raw.githubusercontent.com/jasondavies/d3-cloud/master/build/d3.layout.cloud.js').read()

    output = """<!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <title>twarc wordcloud</title>
    <script src="http://d3js.org/d3.v3.min.js"></script>
    </head>
    <body>
    <script>

      // embed Jason Davies' d3-cloud since it's not available in a CDN
      %s

      var fill = d3.scale.category20();
      var words = %s

      d3.layout.cloud().size([800, 800])
          .words(words)
          .rotate(function() { return ~~(Math.random() * 2) * 90; })
          .font("Impact")
          .fontSize(function(d) { return d.size; })
          .on("end", draw)
          .start();

      function draw(words) {
        d3.select("body").append("svg")
            .attr("width", 1000)
            .attr("height", 1000)
          .append("g")
            .attr("transform", "translate(400,400)")
          .selectAll("text")
            .data(words)
          .enter().append("text")
            .style("font-size", function(d) { return d.size + "px"; })
            .style("font-family", "Impact")
            .style("fill", function(d, i) { return fill(i); })
            .attr("text-anchor", "middle")
            .attr("transform", function(d) {
              return "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")";
            })
            .text(function(d) { return d.text; });
      }
    </script>
    </body>
    </html>
    """ % (wordcloud_js.decode('utf8'), json.dumps(words, indent=2))


    export_uuid = uuid.uuid4()
    with open(os.path.join(EXPORTS_BASEDIR, '{}_wordcloud_UUID_{}.html'.format(q.title, export_uuid)), 'w+') as f:
            f.write(output)
    addExportRef = models.EXPORTS(url='{}_wordcloud_UUID_{}.html'.format(q.title, export_uuid),
                                  type='Wordcloud', exported=datetime.utcnow(), count=None)
    q.exports.append(addExportRef)
    db.session.commit()
    db.session.close()

def text(t):
    if 'full_text' in t:
        return t['full_text']
    return t['text']


