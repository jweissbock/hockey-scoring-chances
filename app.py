from __future__ import with_statement
from flask import Flask, render_template, request, session, g, redirect, url_for, \
	 abort, flash
from urllib2 import urlopen
from contextlib import closing
from bs4 import BeautifulSoup
import re, json, sqlite3, MySQLdb, sqlalchemy
import scrape
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

@app.route('/pbp/')
def pbp():
	return render_template('pbp.html',gameid=20001)

# returns the api instructions
@app.route('/toi/api/')
def toiAPIInstructions():
	return render_template('toi-instructions.html')

@app.route('/toi/api/<int:urlgid>/<int:urlper>/<int:urltrem>')
def toiapp(urlgid=None, urlper=None, urltrem=None):
	# check if urlgid is a digit and 10 
	error = True
	message = "API"
	team1 = []
	team2 = []
	team1name = "team1"
	team2name = "team2"
	if len(str(urlgid)) != 10:
		message = "Not a valid game ID"
	elif urlper not in range(1,7):
		message = "Period is not valid"
	elif urltrem not in range(0,1201):
		message = "Time is not valid."
	else:
		# check if gameid is in db
		# check if anything with selected data
		# return what we have
		sql = "SELECT * FROM shifts WHERE gameid = %s AND shift_start >= %s AND shift_end < %s AND period = %s ORDER BY playerteamname, playernumber+0"
		params = [urlgid, urltrem, urltrem, urlper]
		cur = g.db.execute(sql, params)
		fetchd = cur.fetchall()
		if fetchd != []:
			# turn fetchd into a list, do stuff easier here
			team1name = fetchd[0][5]
			for player in fetchd:
					if player[5] == team1name:
						team1.append(player[3])
					else:
						team2.append(player[3])
						team2name = player[5].title()
			# make fancy lists
			team1name = team1name.title()
			error = False
			message = "ACK"
		else:
			message = "Nothing found for these values"
	return json.dumps({'error' : error, 'message' : message,
						'team1name' : team1name, 'team2name' : team2name,
						'team1' : team1, 'team2' : team2})

# todo for this function
#	+ can enter 3 digit times
#	+ send old values to form (use wtf-forms)
#	+ get name of teams instead of home/away
#	+ adjust for OT2,3...
#	+ adjust for querying an OT that doesnt exist
#	+ make into ajax / API
#	+ prettier box to report numbers.
@app.route('/toi/api/<int:urlgid>/<int:urlper>')
@app.route('/toi/api/<int:urlgid>')
@app.route('/toi/', methods=['GET', 'POST'])
def toi(urlgid=None, urlper=None):
	team1 = None
	team1roster = []
	team2 = None
	team2roster = []
	message = None

	gameidForm = ""
	timeidForm = "20:00"
	api = False

	if request.method == 'POST' or api == True:
		gyear = request.form['gyear']
		gid = request.form['gameid']
		gameid = str(gyear) + '0' + str(gid)
		period = request.form['period']
		time = request.form['time']

		mins = time[:2]
		secs = time[3:5]

		# check if gid is in db
		cur = g.db.execute('SELECT * FROM shifts WHERE gameid=%s', [gameid])

		if not gyear.isdigit() or int(gyear) not in range(2007, 2013):
			message = "Game year is not valid."
		elif not gid.isdigit() or len(gid) != 5:
			message = "Game ID is not valid."
		elif cur.fetchone() is None:
			message = "This game id does not exist in our database."
		elif period not in ['1','2','3', '4']:
			message = "Period is not valid."
		elif not re.match(r'^\d\d:\d\d$', time):
			message = "Time is not in valid format"
		elif int(mins)*60 + int(secs) > 1200: 
			message = "Time is too high."
		else:
			# SELECT * FROM pbp WHERE cast(timedown as integer) >= 1166 AND gid=30151 AND period = 1 ORDER BY gnumber DESC LIMIT 1;
			# SELECT * FROM shifts WHERE gameid = 2012020123 AND shift_start >= 1000 AND shift_end < 1000 AND period = 2 ORDER BY playerteamname, playernumber+0;
			sql = "SELECT * FROM shifts WHERE gameid = %s AND shift_start >= %s AND shift_end < %s AND period = %s ORDER BY playerteamname, playernumber+0"
			queryGameID = int(mins)*60 + int(secs)
			params = [int(gameid), queryGameID, queryGameID, int(period)]
			cur = g.db.execute(sql, params)
			fetchd = cur.fetchall()
			if fetchd != []:
				# turn fetchd into a list, do stuff easier here
				team1 = fetchd[0][5]
				team2 = ""
				for player in fetchd:
						if player[5] == team1:
							team1roster.append(player[3])
						else:
							team2roster.append(player[3])
							team2 = player[5].title()
				# make fancy lists
				team1 = team1.title()
				team1roster = ' <br />'.join(team1roster)
				team2roster = ' <br />'.join(team2roster)
			else:
				message = "Nothing found for these values"
		gameidForm = str(gid)
		timeidForm = time
	return render_template('toi.html', team1=team1, team2=team2,
							team1roster=team1roster, team2roster=team2roster,
							error = message, gameid=gameidForm, timerem=timeidForm)

@app.route('/about')
def about():
  return render_template('about.html')

@app.route('/allgames')
def allgames():
	cur = g.db.execute('SELECT count(*) as numchances, gameid FROM chances GROUP BY gameid ORDER BY gameid DESC')
	bigdata = [list(row) for row in cur.fetchall()]
	return render_template('allgames.html', alldata=bigdata)

#http://www.reddit.com/r/learnpython/comments/1bie5m/new_to_python_flask_web_development_how_can_i/
@app.route('/gamereport/<int:gameid>')
def gamereport(gameid):
	cache = SimpleCache()
	bigdata = []
	try:
		cur = g.db.execute('SELECT team,period,time,comment FROM chances WHERE gameid=%s ORDER BY period, time DESC', 
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
