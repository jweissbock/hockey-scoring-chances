from bs4 import BeautifulSoup
import urllib2
import re

def getGameStates(gameid):
	url = "http://www.nhl.com/scores/htmlreports/20122013/PL0"+str(gameid)+".HTM"

	request = urllib2.Request(url)
	response = urllib2.urlopen(request)

	the_page = response.read()
	soup = BeautifulSoup(the_page)

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
