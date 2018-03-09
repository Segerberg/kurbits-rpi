from flask import Flask,render_template, redirect, url_for, request, session, flash, g, send_from_directory, jsonify, url_for,current_app,Response
from sqlalchemy.ext.declarative import declarative_base
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config.from_object('config')

db = SQLAlchemy(app)

from app import views, models

