from __future__ import with_statement
from flask import Flask, render_template, request, session, g, redirect, url_for, \
	 abort, flash
from urllib2 import urlopen
from contextlib import closing
import re, json, sqlite3

DATABASE = 'hsc.db'
DEBUG = True
SECRET_KEY = 'I Love Don Cherry'
USERNAME = 'admin'
PASSWORD = 'default'

app = Flask(__name__)
app.config.from_object(__name__)

def connect_db():
	return sqlite3.connect(app.config['DATABASE'])

def init_db():
	with closing(connect_db()) as db:
		with app.open_resource('schema.sql') as f:
			db.cursor().executescript(f.read())
		db.commit()

@app.before_request
def before_request():
	g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
	g.db.close()

@app.route('/')
def home():
  return render_template('home.html')

@app.route('/about')
def about():
  return render_template('about.html')

@app.route('/saveGame')
def saveGame():
	n = 6# n = depending on how many items we are saving per puck
	args = sorted(request.args)
	print args
	gameID = request.args.get(args.pop(0))
	gameYear = request.args.get(args.pop(0))
	pucks = len(args) / n #n
	# need to check each elemtn value...
		# team is Home or Away, make numeric
		#period is a number, 1-3,
		# time is 0-1200
		# comment is a value
	# fuck it, delete all events from game ID and save all new ones for now
	# later, find difference between database and what submited, delete from DB insert new ones
	# need to keep a log
	# delete all from this game id and year?
	# while loop not empty
		# pop top n off
		# store into database
	data = [{ 'success' : True, 'gid' : gameID, 'pucks' : pucks }]
	return json.dumps(data)

@app.route('/getGame')
def getGame():
	# check if the id is a valid id
	gameID = request.args.get('gID')
	gYear =  request.args.get('gYear')
	success = True
	if gameID.isdigit() != True:
		success = False
	# check if variables are in regex form
	regexGYear = re.compile("[^d$]{8}")
	regexGID = re.compile("[^d$]{5}")
	if regexGID.search(gameID) == None:
		success = False
	elif regexGYear.search(gYear) == None:
		success = False
	# check if game id is legit
	# e.g. http://www.nhl.com/scores/htmlreports/20122013/PL020232.HTM
	urlData = "http://www.nhl.com/scores/htmlreports/"+gYear+"/PL0"+gameID+".HTM"
	code = 0
	try:
		code = urlopen(urlData).code
	except:
		success = False
	if (code / 100 >= 4):
		success = False
	data = [{'gid' : gameID, 'success' : success}]
	return json.dumps(data)

if __name__ == '__main__':
  app.run()
