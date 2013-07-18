from __future__ import with_statement
from flask import Flask, render_template, request, session, g, redirect, url_for, \
	 abort, flash
from urllib2 import urlopen
from contextlib import closing
from bs4 import BeautifulSoup
import re, json, sqlite3
import scrape
from werkzeug.contrib.cache import SimpleCache

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

@app.route('/pBp')
def pbp():
	return render_template('pbp.html')

@app.route('/about')
def about():
  return render_template('about.html')

@app.route('/allgames')
def allgames():
	cur = g.db.execute('SELECT count(*) as numchances, gameid FROM chances GROUP BY gameid ORDER BY gameid DESC')
	bigdata = [list(row) for row in cur.fetchall()]
	return render_template('allgames.html', alldata=bigdata)

@app.route('/gamereport/<int:gameid>')
def gamereport(gameid):
	cache = SimpleCache()
	bigdata = []
	try:
		cur = g.db.execute('SELECT team,period,time,comment FROM chances WHERE gameid=? ORDER BY period, time DESC', 
						[gameid])
		bigdata = [list(row) for row in cur.fetchall()]
	except:
		# failed to load, quit
		app.logger.error('Unable to load data for game '+str(gameid))
		return 'Unable to load game data for this game'
		

	# if nothing in bigdata now we dont have anything on this team so we abort
	if len(bigdata) == 0:
		return 'Unable to find any game data for this game'

	# get game events from scrape.getGameStates
	# need to find a way to cache it
	events = cache.get('events'+str(gameid))
	if events is None:
		events = scrape.getGameStates(gameid)
		cache.set('events'+str(gameid), events, timeout=60*60*24)

	# for the second/third tables
	gameSummaryHome = {}
	gameSummaryAway = {}

	# the fourt table data periodSummary
	periodSummary = []
	tempPeriodSummary = [1]+[0]*12

	# pass over bigdata with algorithm
	count = 0
	for i, d in enumerate(bigdata):
		searching = True
		while searching:
			if d[1] == events[count][0] and d[2] <= events[count][1] and d[2] > events[count+1][1]:
				# for each player on each team, record scoring chance for/against and at what state
				# use dictionary for each player number with a list
				# here's the part to update the players overall count
				homeNums = events[count][3]
				awayNums = events[count][2]

				chance = d[0]

				home = len(homeNums)
				away = len(awayNums)
				state = str(home-1)+"v"+str(away-1)

				# figures out what type of chance this is for each of the players
				# based on state of the game and if home/away did the chance
				if home == away:
					if chance == 0:
						cLocHome = 3
						cLocAway = 4
					else:
						cLocHome = 4
						cLocAway = 3
				elif home > away:
					if chance == 0:
						cLocHome = 6
						cLocAway = 10
					else:
						cLocHome = 7
						cLocAway = 9
				elif home < away:
					if chance == 0:
						cLocHome = 9
						cLocAway = 7
					else:
						cLocHome = 10
						cLocAway = 6

				# start adding the rows for the inividual players in home and away
				for num in homeNums:
					if num not in gameSummaryHome:
						gameSummaryHome[num] = [num]+[0]*10

					gameSummaryHome[num][cLocHome] += 1

				for num in awayNums:
					if num not in gameSummaryAway:
						gameSummaryAway[num] = [num]+[0]*10

					gameSummaryAway[num][cLocAway] += 1

				# adds data to the final-2 tables, sums of the totals
				# we know the state, we know the period, we can add to the variable
				if d[1] != tempPeriodSummary[0]:
					# new period, reset tempPeriodSummary and append old
					tempPeriodSummary[1] = sum(tempPeriodSummary[3::2])
					tempPeriodSummary[2] = sum(tempPeriodSummary[4::2])
					# sum up totals
					periodSummary.append(tempPeriodSummary)
					tempPeriodSummary = [d[1]] + [0]*12
				
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

				awaydata = events[count][2] + [' ']*(6-len(events[count][2]))
				homedata = events[count][3] + [' ']*(6-len(events[count][3]))
				bigdata[i] = bigdata[i] + homedata + awaydata + [state]
				searching = False
			else:
				count = count + 1

	# pass dictionaries to get all info
	getPlayerInfo = cache.get('getPlayerInfo'+str(gameid))
	if getPlayerInfo is None:
		getPlayerInfo = scrape.getGamePlayerStats(gameSummaryHome, gameSummaryAway, gameid)
		cache.set('getPlayerInfo'+str(gameid), getPlayerInfo, timeout=60*60*24)

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

	# ugly pass over all data and modify it
	for row in bigdata:
		row[0] = "Home" if row[0] == 0 else "Away"
		time = divmod(row[2], 60)
		row[2] = "%d:%02d" % (time[0], time[1])

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
		elif int(request.args.get(puckperiod)) not in range(0,4):
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
		g.db.execute('DELETE FROM chances WHERE gameid = ?', [gameID])
		g.db.commit()
		for p in pucks:
			g.db.execute('INSERT INTO chances (gameid, yearid, team, period, time, comment, posx, posy) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
						[gameID, gameYear, p['team'], p['period'], p['time'], p['comment'], p['left'], p['top']])
			g.db.commit()
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
		cur = g.db.execute('SELECT team, period, time, comment, posx, posy FROM chances WHERE gameid = ? AND yearid = ?', 
							[gameID, gYear])
		pucks = [dict(top=row[5], left=row[4], period=row[1], time=row[2], team=row[0], comment=row[3]) for row in cur.fetchall()]
		getPucks = True
	except:
		getPucks = False

	data = [{'gid' : gameID, 'success' : success, 'getChances' : getPucks, 'chances' : pucks}]
	return json.dumps(data)

if __name__ == '__main__':
  app.run()
