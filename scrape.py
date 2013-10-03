from bs4 import BeautifulSoup
import urllib2
import re
import copy, logging, requests

def getGamePlayerStats(year, homeTeam, awayTeam, gameId):
	# try to open the url so we can get the html and parse it
	print "YEAR: "+str(year)
	url = "http://www.nhl.com/scores/htmlreports/"+str(year)+"/ES0"+str(gameId)+".HTM"

	try:
		request = urllib2.Request(url)
		response = urllib2.urlopen(request)

		the_page = response.read()
		soup = BeautifulSoup(the_page, 'html.parser')
	except:
		logging.error('Failed to load '+url)

	# get the main bod of the html table that contains players on the ice
	rows = soup.findAll('td', 'tborder')[2].findAll("tr", attrs={'class' : re.compile("evenColor|oddColor")})

	numTimes = 0
	team = copy.deepcopy(awayTeam)
	counter = 0

	# go through each row, grab the players name and ice time
	for r in rows:
		counter += 1
		player = r.findAll('td')
		num = player[0].text
		if num == 'TEAM TOTALS':
			if numTimes == 0:
				awayTeam = copy.deepcopy(team)
				team = copy.deepcopy(homeTeam)
			else: 
				pass
			numTimes += 1
			continue

		# check if this player is in the team so only add the appropriate players info
		if num in team:
			team[num][1] = player[2].text
			team[num][2] = player[14].text
			team[num][5] = player[12].text
			team[num][8] = player[13].text

	# prevent the away team from over writting the home team if no rows
	if len(rows) > 0:
		homeTeam = copy.deepcopy(team)

	return [homeTeam, awayTeam]

def getGameStates(year,gameid):
	print "YEAR: "+str(year)
	url = "http://www.nhl.com/scores/htmlreports/"+str(year)+"/PL0"+str(gameid)+".HTM"
	print url

	r = requests.get(url)
	the_page = r.text
	soup = BeautifulSoup(the_page, 'html.parser') 

	rows = soup.findAll("tr", "evenColor")

	events = []

	for r in rows:
		cells = r.findAll("td")
		time = cells[3].text
		time = time[:time.find(":")+3]
		nums = time.split(":")
		time = 1200 - (int(nums[0])*60 + int(nums[1]))

		period = int(cells[1].text)

		awayOnIce = cells[6].findAll('font')
		awayOnIce = [x.text for x in awayOnIce]
		awayOnIce = ' '.join(awayOnIce)
		awayOnIce = awayOnIce.split()

		homeOnIce = cells[6].findNextSiblings('td')[0].text
		homeOnIce = ' '.join(homeOnIce.split())
		homeOnIce = re.sub("[^0-9 ]", "", homeOnIce)
		homeOnIce = homeOnIce.split()

		if len(homeOnIce) > 0:
			events.append([period, time] + [awayOnIce] + [homeOnIce])

	return events
