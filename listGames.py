import requests
from bs4 import BeautifulSoup

r = requests.get('http://www.nhl.com/ice/schedulebyseason.htm?season=20082009&gameType=3&team=&network=&venue=')
soup = BeautifulSoup(r.text, "html5lib")

for row in soup.findAll('table', 'data schedTbl')[0].findAll('tr'):
	btn = row.findAll('a', 'btn')
	if len( btn ) == 0: continue
	print btn[0]['href'].split("?id=")[1]
