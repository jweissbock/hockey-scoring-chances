import MySQLdb
import sqlalchemy
import sqlite3
import requests, re
from bs4 import BeautifulSoup

engine = sqlalchemy.create_engine('mysql://root:password@localhost/hsc')
myDB = sqlite3.connect('hsc.db')

def insertMysql():
	cur = myDB.execute("SELECT * FROM pbp")

	print "trying to insert"

	for i in cur:
		sql = "INSERT INTO pbp (gid, gnumber, period, timeup, timedown, event, description, v1, v2, v3, v4, v5, v6, h1, h2, h3, h4, h5, h6) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)" 
		values = list(i)[1:]
		engine.execute(sql, values)

	print "finished inserting all values"

# need to redo 2012030161
# need to deal with more players on ice
# need to swithc to time on ice sheets

def pbpinsert(gameid):
	# redo game id, split and calculate
	gid = gameid
	year = str(gameid)[:4]+str(int(str(gameid)[:4])+1)
	gameid = str(gameid)[5:]

	cur = myDB.execute('SELECT id FROM pbp WHERE gid=?', [gid])
	fetchd = cur.fetchone()
	if fetchd is not None:
		return gameid
		# need something here to ID those who have something already

	url = "http://www.nhl.com/scores/htmlreports/"+year+"/PL0"+gameid+".HTM"

	r = requests.get(url)
	the_page = r.text
	soup = BeautifulSoup(the_page, 'html.parser') 

	rows = soup.findAll("tr", "evenColor")

	events = []

	for r in rows:
		cells = r.findAll("td")
		gnumber = int(cells[0].text)

		time = cells[3].text
		time = time[:time.find(":")+3]
		nums = time.split(":")
		try:
			timeup = (int(nums[0])*60 + int(nums[1]))
		except:
			continue
		timedown = 1200 - timeup

		period = int(cells[1].text)
		event = cells[4].text
		description = cells[5].text

		awayOnIce = cells[6].findAll('font')
		awayOnIce = [x.text for x in awayOnIce]
		awayOnIce = ' '.join(awayOnIce)
		awayOnIce = awayOnIce.split()

		homeOnIce = cells[6].findNextSiblings('td')[0].text
		homeOnIce = ' '.join(homeOnIce.split())
		homeOnIce = re.sub("[^0-9 ]", "", homeOnIce)
		homeOnIce = homeOnIce.split()

		# check len of
		if len(homeOnIce) < 6:
			homeOnIce += [-1]*(6-len(homeOnIce))
		if len(awayOnIce) < 6:
			awayOnIce += [-1]*(6-len(awayOnIce))

		newPBPdata = [gid, gnumber, period, timeup, timedown, event, description] + awayOnIce + homeOnIce	
		newPBPdata = tuple(newPBPdata)

		sql = "INSERT INTO pbp (gid, gnumber, period, timeup, timedown, event, description, v1, v2, v3, v4, v5, v6, h1, h2, h3, h4, h5, h6) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"

		# insert into db	
		try:			
			# save each item
			myDB.execute(sql, newPBPdata)
			myDB.commit()
		except Exception, err:
			print "FAILED TO INSERT: ",
			print str(err)
			print newPBPdata
			pass

	return -1

def pbp():
	# no game ids to run at this time
	gamesIDs = []
	fails = []
	for gid in gamesIDs:
		print gid
		value = pbpinsert(gid)
		if value > -1:
			fails.append(value) 
			print "%s FAILED" % (value)