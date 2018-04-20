from flask_wtf import FlaskForm
from app import models, db
from wtforms import StringField, BooleanField, SelectField, RadioField , FieldList, FormField, TextAreaField, SelectMultipleField, widgets,validators, PasswordField
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired,Regexp
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField

def collection():
    return db.session.query(models.COLLECTION).all()


class collectionAddForm(FlaskForm):
    assoc = QuerySelectField(u'Collection Name', query_factory=collection, get_label='title')


class twitterTargetForm(FlaskForm):
    title = StringField(u'Title', validators=[DataRequired()])
    searchString = StringField(u'Search ')
    #searchLang = SelectField('Search Language', choices=[(None,"Not specified"),("sv","sv"),("en","en")])
    searchLang = SelectField(u'Search language', choices=[], coerce=str)
    creator = StringField(u'Creator')
    description = TextAreaField(u'Description')
    subject = StringField(u'Subject')
    status = SelectField(u'Status', choices=[("1", "Active"),("0","Closed")])
    index = BooleanField(u'Index')



class twitterCollectionForm(FlaskForm):
    title = StringField(u'Title', validators=[DataRequired()])
    curator = StringField(u'Curator')
    description = TextAreaField(u'Description')
    collectionType = SelectField(u'Collection Type', choices=[], coerce=str)
    subject = StringField(u'Subject')
    status = SelectField(u'Status', choices=[("1", "Active"),("0","Closed")])
    inclDateStart = DateField(u'Inclusive start date',[validators.Optional()],format='%Y-%m-%d')
    inclDateEnd = DateField(u'Inclusive end date',[validators.Optional()],format='%Y-%m-%d')


class SearchForm(FlaskForm):
    search = StringField('search', validators=[DataRequired()])


class twitterTrendForm(FlaskForm):
    geoloc = StringField(u'geo location', validators=[DataRequired(),Regexp(message='Not a valid geolocation, sorry.',regex="^[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)$")])


class stopWordsForm(FlaskForm):
    stopWord = StringField(u'Stop Word', validators=[DataRequired()])

class collectionTypeForm(FlaskForm):
    type = StringField(u'Collection Type', validators=[DataRequired()])

class langCodeForm(FlaskForm):
    type = StringField(u'Collection Type', validators=[DataRequired()])

SCHEDULE_CHOICES = [('604800', 'Weekly'), ('86400', 'Daily'),('43200', 'Twice a day'),
                                            ('21600', 'Four times a day'),('10800', 'Every third hour'),
                                            ('3600', 'Hourly'),('60', 'Every minute')]
class scheduleForm(FlaskForm):
    schedule = SelectField(u'Schedule', choices=SCHEDULE_CHOICES)

class passwordForm(FlaskForm):
    password = PasswordField('New Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')
