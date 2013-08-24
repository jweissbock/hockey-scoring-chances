from __future__ import with_statement
from flask import Flask, render_template, request, session, g, redirect, url_for, \
	 abort, flash
from flask.ext.classy import FlaskView, route
import fnmatch, re

class pbp(FlaskView):
	def index(self):
		message = None
		getURL = request.args.get('gameid')
		gameid = 20001
		if getURL is not None:
			message = "Game ID %s is not valid." % (getURL)
		return render_template('pbp.html',gameid=gameid, error=message)

	def post(self):
		gameid = request.form['gameid']
		event = request.form['event']
		gyear = request.form['gyear']
		# is event in 1,2,3
		if event not in [str(x) for x in range(1,4)]:
			message = "Event is not valid."
		# is gyear in 2007-2012
		elif gyear not in [str(x) for x in range(2007,2013)]:
			message = "Game year is not valid."
		# is gameid a 5 digit int
		elif not gameid.isdigit() or len(gameid) != 5:
			message = "Game id << %s >> is not valid" % (gameid)
		else: 
			if event == '1': event = 'zs'
			elif event == '2': event = 'pen'
			else: event = 'SA'
			fullGame = gyear +"0"+gameid
			return redirect(url_for('pbp:getpbpZS', event=event, urlfullgame=fullGame)) 
		return render_template('pbp.html',gameid=gameid, error=message)

	@route('/<event>/<int:urlfullgame>/')
	def getpbpZS(self,event,urlfullgame):
		returnGame = int(str(urlfullgame)[5:])
		if len(str(urlfullgame)) != 10:
			return redirect(url_for('pbp:index', gameid=returnGame))
		elif event.upper() not in ['ZS', 'PEN', 'SA']:
			return redirect(url_for('pbp:index', gameid=returnGame))
		else:
			gameid = str(urlfullgame)[5:]
			gyear = str(urlfullgame)[:4]
			if event.upper() == 'ZS': return self.pbpZS(gameid, gyear)
			elif event.upper() == 'PEN': return self.pbpPEN(gameid, gyear)
			elif event.upper() == 'SA': return self.pbpSA(gameid, gyear)

	# return the table for penalties
	def pbpSA(self,gameid, gyear):
		searchGame = int(gyear+"0"+gameid)
		# is this gameid in pbp data
		sql = "SELECT * FROM pbp WHERE gid = %s AND (event = 'GOAL' or event = 'SHOT' or event = 'MISS' or event = 'BLOCK')"
		params = [searchGame]
		cur = g.db.execute(sql, params)
		pbp = cur.fetchall()
		if pbp == []:
			return redirect(url_for('pbp:index', gameid=gameid))
		else:
			table = []
			for row in pbp:
				# convert time to readable
				timeup = "%s:%s" % (divmod(row[4], 60))
				timedown = "%s:%s" % (divmod(row[5], 60))
				if len(timeup) - (timeup.index(':')+1) == 1: timeup = timeup + "0"
				if len(timedown) - (timedown.index(':')+1) == 1: timedown = timedown + "0"
				# get the team
				rowSplit = row[7].split()
				team = rowSplit[0]
				# get the Shooter
				shooter = rowSplit[rowSplit.index(fnmatch.filter(rowSplit, '#*')[0])+1]
				#if ')' == shooter.strip()[-1]: shooter = shooter[:-3]
				shooter = re.sub('\(\d\)','', shooter.rstrip())
				shooter = shooter.replace(',','')
				# type of shot
				typeShot = ['Backhand', 'Snap', 'Slap', 'Tip-In', 'Wrist']
				typeShot = ''.join([x for x in typeShot if x.lower() in row[7].lower()])
				# distance
				distance = re.findall(r'(\d+ ft.)', row[7])
				distance = ''.join(distance)
				# home and visitors
				homeList = [str(x) for x in [row[14], row[15], row[16], row[17], row[18], row[19]] if x > -1]
				awayList = [str(x) for x in [row[8], row[9], row[10], row[11], row[12], row[13]] if x > -1]
				homeNum = len(homeList)-1 # count them for the state
				awayNum = len(awayList)-1
				homeList = homeList+[""]*(5-homeNum) # add empty pers if missing man
				awayList = awayList+[""]*(5-awayNum)
				# state 
				state = str(awayNum)+"v"+str(homeNum)
				# situation
				if awayNum == homeNum: situation = "ES"
				elif awayNum > homeNum: situation = "PP"
				else: situation = "SH"
				# return the data
				data = [row[3], timeup, timedown, team, shooter, row[6], typeShot, distance, 
						state, situation] + awayList + homeList
				table.append(data)
			return render_template('pbp-sa.html', table=table)


	# return the table for penalties
	def pbpPEN(self,gameid, gyear):
		searchGame = int(gyear+"0"+gameid)
		# is this gameid in pbp data
		sql = "SELECT * FROM pbp WHERE gid = %s and event = 'PENL' ORDER BY id, timedown DESC"
		params = [searchGame]
		cur = g.db.execute(sql, params)
		pbp = cur.fetchall()
		if pbp == []:
			return redirect(url_for('pbp:index', gameid=gameid))
		else:
			table = []
			for row in pbp:
				# convert time to readable
				timeup = "%s:%s" % (divmod(row[4], 60))
				timedown = "%s:%s" % (divmod(row[5], 60))
				if len(timeup) - (timeup.index(':')+1) == 1: timeup = timeup + "0"
				if len(timedown) - (timedown.index(':')+1) == 1: timedown = timedown + "0"
				# get the penalty
				penalty = row[7].replace('\xc2','')
				penalty = penalty.replace('\xa0',' ')
				# get the offender name
				if '#' in penalty[:penalty.index('min)')]:
					offender = penalty.split()[2]# perso
				else:
					offender = ' '.join(penalty.split()[:2]) # team offender
				# get the infraction
				infraction = penalty[penalty.index(offender)+len(offender):penalty.index('(')].strip()
				# get the drawn by
				if 'bench' in penalty: drawer = None	
				else: drawer = penalty.split()[-1]
				# length	
				print penalty
				length = penalty[penalty.index('(')+1:penalty.index(' min)')]
				data = [row[3], timeup, timedown, offender, infraction, drawer, length]
				table.append(data)
			return render_template('pbp-pen.html', table=table)

	# returns the table for zone entries
	def pbpZS(self, gameid, gyear):
		searchGame = int(gyear+"0"+gameid)
		# is this gameid in pbp data
		sql = "SELECT * FROM pbp WHERE gid = %s and event = 'FAC' ORDER BY id, timedown DESC"
		params = [searchGame]
		cur = g.db.execute(sql, params)
		pbp = cur.fetchall()
		if pbp == []:
			return redirect(url_for('pbp:index', gameid=gameid))
		else:
			table = []
			homeStats = {}
			awayStats = {}
			hTable = []	# individual table for stats
			aTable = []
			for row in pbp:
				homeList = [str(x) for x in [row[14], row[15], row[16], row[17], row[18], row[19]] if x > -1]
				awayList = [str(x) for x in [row[8], row[9], row[10], row[11], row[12], row[13]] if x > -1]
				homeNum = len(homeList)-1
				awayNum = len(awayList)-1
				homeList = homeList+[""]*(5-homeNum)
				awayList = awayList+[""]*(5-awayNum)
				# state 
				state = str(awayNum)+"v"+str(homeNum)
				# situation
				if awayNum == homeNum: situation = "ES"
				elif awayNum > homeNum: situation = "PP"
				else: situation = "SH"
				# convert time to readable
				timeup = "%s:%s" % (divmod(row[4], 60))
				timedown = "%s:%s" % (divmod(row[5], 60))
				if len(timeup) - (timeup.index(':')+1) == 1: timeup = timeup + "0"
				if len(timedown) - (timedown.index(':')+1) == 1: timedown = timedown + "0"
				# location
				text = row[7]
				location = text[text.index('won')+4:text.index('-')-1]
				# player data
				for l in [homeList, awayList]:
					stats = homeStats if l == homeList else awayStats
					for p in l:
						if p not in stats: stats[p] = [0,0,0]
						if 'Def' in location: index = 0
						elif 'Neu' in location: index = 1
						else: index = 2
						stats[p][index] += 1
				# final	
				datum = [row[3], timeup, timedown, state, situation, location]+homeList+awayList
				table.append(datum)
			# convert players to list
			for players in [homeStats, awayStats]:
				itable = hTable if players == homeStats else aTable
				for p in sorted(players.iterkeys()):
					sql = "SELECT playername FROM shifts WHERE gameid=%s AND playernumber = %s GROUP BY playername ORDER BY ID LIMIT 1;"
					if players == awayStats:
						sql = "SELECT playername FROM shifts WHERE gameid=%s AND playernumber = %s GROUP BY playername ORDER BY ID DESC LIMIT 1;"
					try:
						pNum = int(p)
					except: 
						continue
					params = [searchGame, pNum]
					cur = g.db.engine.execute(sql, params)
					name = cur.fetchone()
					itable.append([name[0]]+players[p])
			return render_template('pbp-zones.html', table=table, 
										hTable=hTable, aTable=aTable)
