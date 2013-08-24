from __future__ import with_statement
from flask import Flask, render_template, request, session, g, redirect, url_for, \
	 abort, flash
from flask.ext.classy import FlaskView

class apps(FlaskView):
	def index(self):
		return render_template('allapps.html')
