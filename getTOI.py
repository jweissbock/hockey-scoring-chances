import MySQLdb
import sqlalchemy
import requests, re, csv
from bs4 import BeautifulSoup

engine = sqlalchemy.create_engine('mysql://root:password@localhost/hsc')

# redo 2012020124

def getGameTOI(gameid):
	# assume gameid in yyyy0ddddd
	year = str(gameid)[:4]+str(int(str(gameid)[:4])+1)
	digit = str(gameid)[5:]

	home = "http://www.nhl.com/scores/htmlreports/%s/TH0%s.HTM" % (year, digit)
	away = "http://www.nhl.com/scores/htmlreports/%s/TV0%s.HTM" % (year, digit)

	for url in [home, away]:
		try:
			parsePage(url, gameid)
		except:
			pass

def parsePage(url, gameid):
	r = requests.get(url)
	soup = BeautifulSoup(r.text, "html.parser")

	# get the main table
	table = soup.findAll('table', 'tablewidth')[0].findAll('table')

	# get the team name
	teamName = table[7].text.strip()

	table = table[8]

	#get all the players first
	roster = table.findAll('td', 'playerHeading')

	#print teamName

	# location
	location = 'h' if 'TH0' in url else 'v'

	rosterNum = -1
	for item in table.findAll("tr", { "class" : re.compile(r"^(playerHeading|oddColor|evenColor)$") }):
		cells = item.findAll('td')
		# skip the summary rows
		if len(cells) != 6: continue
		# get all the cells
		shiftNum = int(cells[0].text)
		period = cells[1].text
		shiftStart = cells[2].text.split('/')[1].strip()
		shiftStart = sum(int(x) *60 ** i for i,x in enumerate(reversed(shiftStart.split(":"))))
		shiftEnd = cells[3].text.split('/')[1].strip()
		shiftEnd = sum(int(x) *60 ** i for i,x in enumerate(reversed(shiftEnd.split(":"))))
		event = cells[5].text

		if period == 'OT': period = 4
		else: period = int(period)
		# update the rosterNum on new player
		if shiftNum == 1:
			rosterNum += 1
		# print player name
		ros = roster[rosterNum].text.split(' ', 1)
		if ros[0] == '': continue
		# prepare the sql value
		params = [gameid, int(ros[0]), ros[1], teamName, period, shiftStart, shiftEnd, event, location]
		sql = "INSERT INTO shifts (gameid, playernumber, playername, playerteamname, period, shift_start, shift_end, event, location) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
		engine.execute(sql, params)
		# printing the row data
		#print params
		# insert into database

# load all games
"""allGames = []
with open('games.csv', 'rb') as f:
	reader = csv.reader(f)
	for row in reader:
		allGames.append(row[0])

for game in allGames:
	print game
	getGameTOI(game)"""

#getGameTOI(2012020005)