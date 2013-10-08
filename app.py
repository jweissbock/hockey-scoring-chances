from __future__ import with_statement
from flask import Flask, render_template, request, session, g, redirect, url_for, \
	 abort, flash
from urllib2 import urlopen
from contextlib import closing
from bs4 import BeautifulSoup
import re, json, sqlite3, MySQLdb, sqlalchemy
import scrape, getTOI
from werkzeug.contrib.cache import SimpleCache

#DATABASE = 'hsc.db'
DEBUG = True
SECRET_KEY = 'I Love Don Cherry'
USERNAME = 'admin'
PASSWORD = 'default'

app = Flask(__name__)
app.config.from_object(__name__)

def connect_db():
	return sqlalchemy.create_engine('mysql://root:password@localhost/hsc')

# need a new function dealing with initializing database from schema
def init_db():
	pass

@app.before_request
def before_request():
	g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
	g.db.dispose()

@app.route('/')
def home():
  return render_template('home.html')

from views.allapps import apps
apps.register(app)

from views.pbp import pbp
pbp.register(app)

# returns the api instructions
from views.toi import toi
toi.register(app)

@app.route('/about')
def about():
  return render_template('about.html')

@app.route('/allgames')
def allgames():
	cur = g.db.execute('SELECT count(*) as numchances, gameid, yearid FROM chances GROUP BY yearid, gameid ORDER BY yearid DESC, gameid DESC')
	bigdata = [list(row) for row in cur.fetchall()]
	return render_template('allgames.html', alldata=bigdata)

#http://www.reddit.com/r/learnpython/comments/1bie5m/new_to_python_flask_web_development_how_can_i/
@app.route('/gamereport/<int:year>/<int:gameid>')
def gamereport(year,gameid):
	# check if there are any chances tracked, if not exit
	bigdata = []
	# for the second/third tables
	gameSummaryHome = {}
	gameSummaryAway = {}
	# the fourt table data periodSummary
	periodSummary = []
	tempPeriodSummary = [1]+[0]*12
	try:
		cur = g.db.execute('SELECT team,period,time,comment FROM chances WHERE yearid=%s AND gameid=%s ORDER BY period, time DESC', 
						[year,gameid])
		mydata = [list(row) for row in cur.fetchall()]
	except Exception as e:
		# failed to load, quit
		app.logger.error('Unable to load data for game '+str(gameid))
		return 'There is no saved data for this game.  Did you not press save?'+str(e)

	# count chances
	if len(mydata) == 0:
		return 'There is no saved data for this game.  Did you forget to press save?'

	gameid = int(str(year)[0:4] + "0" + str(gameid)[0:5])

	# check if there is any TOI data for this game.  If not, parse it
	cur = g.db.execute('SELECT * FROM shifts WHERE gameid = %s', [gameid])
	shifts = cur.fetchall()
	if len(shifts) == 0:
		getTOI.getGameTOI(gameid)

	for chance in mydata:
		timeOfChance = chance[2]
		m,s = divmod(timeOfChance, 60)
		chance[2] = "%d:%02d" % (m, s)
		bigdata.append(chance)
		sql = "SELECT playernumber FROM shifts WHERE gameid = %s AND shift_start >= %s AND shift_end < %s AND period = %s AND location = %s ORDER BY playerteamname, playernumber+0"
		# get all home players for this time
		data = [gameid, timeOfChance, timeOfChance, chance[1], 'h']
		cur = g.db.execute(sql, data)
		homeNum = [x[0] for x in cur.fetchall()]
		# get all away players
		data[-1] = 'v'
		cur = g.db.execute(sql, data)
		awayNum = [x[0] for x in cur.fetchall()]

		home = len(homeNum)
		away = len(awayNum)

		# calculate the state
		state = str(home-1)+'v'+str(away-1)

		print home
		print away
		print chance[0]

		# figures out what type of chance this is for each of the players
		# based on state of the game and if home/away did the chance
		if home == away:
			if chance[0] == 0:
				cLocHome = 3
				cLocAway = 4
			else:
				cLocHome = 4
				cLocAway = 3
		elif home > away:
			if chance[0] == 0:
				cLocHome = 6
				cLocAway = 10
			else:
				cLocHome = 7
				cLocAway = 9
		elif home < away:
			if chance[0] == 0:
				cLocHome = 9
				cLocAway = 7
			else:
				cLocHome = 10
				cLocAway = 6

		# start adding the rows for the inividual players in home and away
		for num in homeNum:
			if num not in gameSummaryHome:
				gameSummaryHome[num] = [num]+[0]*10

			gameSummaryHome[num][cLocHome] += 1

		for num in awayNum:
			if num not in gameSummaryAway:
				gameSummaryAway[num] = [num]+[0]*10

			gameSummaryAway[num][cLocAway] += 1

		# adds data to the final-2 tables, sums of the totals
		# we know the state, we know the period, we can add to the variable
		if chance[1] != tempPeriodSummary[0]:
			# new period, reset tempPeriodSummary and append old
			tempPeriodSummary[1] = sum(tempPeriodSummary[3::2])
			tempPeriodSummary[2] = sum(tempPeriodSummary[4::2])
			# sum up totals
			periodSummary.append(tempPeriodSummary)
			tempPeriodSummary = [chance[1]] + [0]*12
		
		# figure out which column to add to
		if state in ["5v5", "4v4", "3v3"]:
			periodPos = 3 if chance == 0 else 4
		elif state == "5v4":
			periodPos = 5 if chance == 0 else 6
		elif state == "5v4":
			periodPos = 7 if chance == 0 else 8
		elif state == "4v5":
			periodPos = 9 if chance == 0 else 10
		else:
			# it must be 3v5
			periodPos = 11 if chance == 0 else 12

		# add to tempPeriodSummary
		tempPeriodSummary[periodPos] += 1

		# pad out the team numbers
		homeNum += [' ']*(6-home)
		awayNum += [' ']*(6-away)
		if state != '-1v-1':
			chance += homeNum
			chance += awayNum
			chance.append(state)
		else: chance += "Invalid Data "

		# make the team readable
		chance[0] = "Home" if chance[0] == 0 else "Away"

	# display big data table
	getPlayerInfo = scrape.getGamePlayerStats(year, gameSummaryHome, gameSummaryAway, str(gameid)[-5:])

	gameSummaryHome = [getPlayerInfo[0][x] for x in getPlayerInfo[0]]
	gameSummaryHome.sort(key = lambda row : int(row[0]))
	gameSummaryAway = [getPlayerInfo[1][x] for x in getPlayerInfo[1]]
	gameSummaryAway.sort(key = lambda row: int(row[0]))

	# update periodSummary
	tempPeriodSummary[1] = sum(tempPeriodSummary[3::2])
	tempPeriodSummary[2] = sum(tempPeriodSummary[4::2])
	periodSummary.append(tempPeriodSummary)

	# awayPeriodSummary
	awayPeriodSummary = [x[:] for x in periodSummary]
	for row in awayPeriodSummary:
		row[1],row[2] = row[2],row[1]
		row[3],row[4] = row[4],row[3]
		row[5],row[10] = row[10],row[5]
		row[6],row[9] = row[9],row[6]
		row[7],row[12] = row[12],row[7]
		row[8],row[11] = row[11],row[8]
	# swap 3<->4,5<->10,6<->9,7<->12,8<->11,1<->2  

	return render_template('gamereport.html', data=bigdata, homeSummary=gameSummaryHome, 
							awaySummary=gameSummaryAway, periodSummary=periodSummary,
							awayPeriodSum=awayPeriodSummary)

@app.route('/saveGame')
def saveGame():
	n = 6# n = depending on how many items we are saving per puck
	msg = "Not working yet."
		# check if number - 2 % n = 0 to see if has right # parameters
	if ((len(request.args) - 2) % n > 0):
		json.dumps([{ 'success' : False, 'msg' : 'Invalid number of arguements.' }])
	args = sorted(request.args)
	#print args
	# need to check if these are valid
	gameID = request.args.get('gameID')
	gameYear = request.args.get('gameYear') 
	numPucks = (len(args)-2) / n 
	pucks = [dict() for x in range(numPucks)]
	# fill up the pucks
	for i in range(numPucks):
		# comment
		comment = 'puck'+str(i)+'comment'
		if comment not in request.args:
			return json.dumps({'success': False, 'msg' : 'No puck comment for '+str(i)})
		pucks[i]['comment'] = request.args.get(comment).strip()
		# puck position
		puckleft = 'puck'+str(i)+'left'
		pucktop = 'puck'+str(i)+'top'
		if pucktop not in request.args or puckleft not in request.args:
			return json.dumps({'success' : False, 'msg' : 'Missing puck location data for '+str(i)})
		elif not request.args.get(puckleft).isdigit():
			return json.dumps({'success' : False, 'msg' : 'Puck left is not a digit for '+str(i)})
		elif not request.args.get(pucktop).isdigit():
			return json.dumps({'success' : False, 'msg' : 'Puck top is not a digit for '+str(i)})
		pucks[i]['left'] = int(request.args.get(puckleft))
		pucks[i]['top'] = int(request.args.get(pucktop))
		# puck time
		pucktime = 'puck'+str(i)+'time'
		if pucktime not in request.args:
			return json.dumps({'success' : False, 'msg' : 'Missing puck time data for '+str(i)})
		elif not request.args.get(pucktime).isdigit():
			return json.dumps({'success' : False, 'msg' : 'Puck time is not a digit for '+str(i)})
		elif not float(request.args.get(pucktime)).is_integer():	
			return json.dumps({'success' : False, 'msg' : 'Puck time is not an integer for '+str(i)})
		elif int(request.args.get(pucktime)) not in range(0,1201):
			return json.dumps({'success' : False, 'msg' : 'Puck time is not an allowable range for '+str(i)})
		pucks[i]['time'] = int(request.args.get(pucktime))
		# puck period
		puckperiod = 'puck'+str(i)+'period'
		if puckperiod not in request.args:
			return json.dumps({'success' : False, 'msg' : 'Missing puck period data for '+str(i)})
		elif not request.args.get(puckperiod).isdigit():
			return json.dumps({'success' : False, 'msg' : 'Puck period is not a digit for '+str(i)})
		elif int(request.args.get(puckperiod)) not in range(0,5):
			return json.dumps({'success' : False, 'msg' : 'Puck period is not an allowable range for '+str(i)})
		pucks[i]['period'] = int(request.args.get(puckperiod))
		#Puck team
		puckteam = 'puck'+str(i)+'team'
		if puckteam not in request.args:
			return json.dumps({'success': False, 'msg' : 'No puck team for '+str(i)})
		if request.args.get(puckteam) == 'Home':
			pucks[i]['team'] = 0
		else:
			pucks[i]['team'] = 1
	#print pucks
	# begin transaction
	# delete all events from game ID and save all new ones for now
	#g.db.execute('BEGIN TRANSACTION')
	try:
		g.db.execute('DELETE FROM chances WHERE gameid = %s', [gameID])
		for p in pucks:
			g.db.execute('INSERT INTO chances (gameid, yearid, team, period, time, comment, posx, posy) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
						[gameID, gameYear, p['team'], p['period'], p['time'], p['comment'], p['left'], p['top']])
	except:
		return json.dumps({ 'success' : False, 'msg' : 'Error in saving to database'})
	#g.db.execute('COMMIT')
	# later, find difference between database and what submited, delete from DB insert new ones
	# need to keep a log
	msg = 'Saved!'
	data = [{ 'success' : True, 'msg' : msg}]
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
	# get all puck data
	pucks = []
	try:
		cur = g.db.execute('SELECT team, period, time, comment, posx, posy FROM chances WHERE gameid = %s AND yearid = %s', 
							[gameID, gYear])
		pucks = [dict(top=row[5], left=row[4], period=row[1], time=row[2], team=row[0], comment=row[3]) for row in cur.fetchall()]
		getPucks = True
	except:
		getPucks = False

	data = [{'gid' : gameID, 'success' : success, 'getChances' : getPucks, 'chances' : pucks}]
	return json.dumps(data)

if __name__ == '__main__':
  app.run()
