import os
import time
import datetime
import scraper_utils
import graph_engine

from flask import Flask, render_template, send_from_directory, request
from scraper_utils import *
from datetime import *
from mongoengine import *
from graph_engine import *
#----------------------------------------
# Utilities
#----------------------------------------


#----------------------------------------
# initialization
#----------------------------------------

app = Flask(__name__)

connect('flight_scraper')

app.config.update(
    DEBUG = True,
)

#----------------------------------------
# controllers
#----------------------------------------
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'ico/favicon.ico')

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/query", methods=['GET'])
def query():
    origin = request.args.get('origin')
    dest = request.args.get('dest')
    freq = request.args.get('freq')
    start_date = request.args.get('start_date')
    until_date = request.args.get('until_date')
    weekdays = request.args.getlist('weekdays')


    start_date = datetime.strptime(start_date, '%m-%d-%Y')
    until_date = datetime.strptime(until_date, '%m-%d-%Y')
    weekdays = map(int, weekdays)

    if freq == "DAILY":
        freq=DAILY

    date_pairs = generate_date_pairs(freq, weekdays, start_date, until_date)

    result = list()

    for d in date_pairs:
        v = [d[0].isoformat(), d[1].isoformat(), search_flights(d, origin, dest)]
        result.append(v)

    return render_template('query.html', result=result)


@app.route("/graph", methods=['GET'])
def graph():
    origin = request.args.get('origin')
    dest = request.args.get('dest')
    dept = request.args.get('dept')
    ret = request.args.get('ret')

    dept = datetime.strptime(dept, '%m-%d-%Y')
    ret = datetime.strptime(ret, '%m-%d-%Y')

    return render_template('graph.html', json_obj=graph_prices(origin, dest, dept, ret))

#----------------------------------------
# launch
#----------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)


