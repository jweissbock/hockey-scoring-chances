from flask import Flask, render_template, request
import json

app = Flask(__name__)

@app.route('/')
def home():
  return render_template('home.html')

@app.route('/about')
def about():
  return render_template('about.html')

@app.route('/getGame')
def getGame():
	data = [{'gid' : request.args.get('gID')}]
	return json.dumps(data)

if __name__ == '__main__':
  app.run(debug=True)
