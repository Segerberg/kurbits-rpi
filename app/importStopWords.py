from app import  models, db
'''
with open ('stop_words_sv.txt', 'rt') as f:
    for line in f:
        if '\n' in line:

            add_stop_words = models.STOPWORDS(stop_word=line.replace('\n',''),lang='sv')
            db.session.add(add_stop_words)
        else:
            add_stop_words = models.STOPWORDS(stop_word=line, lang='en')
            db.session.add(add_stop_words)

db.session.commit()
'''

q = models.STOPWORDS.query.all()
p =set([])
for line in q:
    p.add(line.stop_word)
    #print (line.stop_word)
print (p)