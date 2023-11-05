from flask import Flask, request, render_template
import os
import random
import redis
import socket
import sys
import logging
from datetime import datetime
from opencensus.trace.tracer import Tracer
from opencensus.ext.azure.log_exporter import AzureLogHandler, AzureEventHandler
from opencensus.ext.azure import metrics_exporter
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.ext.flask.flask_middleware import FlaskMiddleware

# App Insights
# Import required libraries for App Insights

# Logging
logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler(connection_string='InstrumentationKey=3043bfcf-9ea9-450b-ae19-7ddc569825b5'))
logger.addHandler(AzureEventHandler(connection_string='InstrumentationKey=3043bfcf-9ea9-450b-ae19-7ddc569825b5'))

# Metrics
exporter = metrics_exporter.new_metrics_exporter(
  enable_standard_metrics=True,
  connection_string='InstrumentationKey=3043bfcf-9ea9-450b-ae19-7ddc569825b5')

# Tracing
tracer = Tracer(
    exporter=AzureExporter(
        connection_string='InstrumentationKey=3043bfcf-9ea9-450b-ae19-7ddc569825b5'),
    sampler=ProbabilitySampler(1.0),
)

app = Flask(__name__)

# Requests
middleware = FlaskMiddleware(
    app,
    exporter=AzureExporter(connection_string="InstrumentationKey=75b36801-bb3d-44fa-aa62-8fa210b1178b"),
    sampler=ProbabilitySampler(rate=1.0),
)

# Load configurations from environment or config file
app.config.from_pyfile('config_file.cfg')

if ("VOTE1VALUE" in os.environ and os.environ['VOTE1VALUE']):
    button1 = os.environ['VOTE1VALUE']
else:
    button1 = app.config['VOTE1VALUE']

if ("VOTE2VALUE" in os.environ and os.environ['VOTE2VALUE']):
    button2 = os.environ['VOTE2VALUE']
else:
    button2 = app.config['VOTE2VALUE']

if ("TITLE" in os.environ and os.environ['TITLE']):
    title = os.environ['TITLE']
else:
    title = app.config['TITLE']

# Redis Connection
r = redis.Redis()

# Change title to host name to demo NLB
if app.config['SHOWHOST'] == "true":
    title = socket.gethostname()

# Init Redis
if not r.get(button1): r.set(button1,0)
if not r.get(button2): r.set(button2,0)

@app.route('/', methods=['GET', 'POST'])
def index():

    if request.method == 'GET':

        # Get current values
        vote1 = r.get(button1).decode('utf-8')
        # use tracer object to trace cat vote
        tracer.span(name="Total {} Voted: {}".format(button1, vote1))

        vote2 = r.get(button2).decode('utf-8')
        # use tracer object to trace dog vote
        tracer.span(name="Total {} Voted: {}".format(button2, vote2))

        # Return index with values
        return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

    elif request.method == 'POST':

        if request.form['vote'] == 'reset':
            # Empty table and return results
            r.set(button1,0)
            r.set(button2,0)
            vote1 = r.get(button1).decode('utf-8')
            properties = {'custom_dimensions': {'Cats Vote': vote1}}
            # use logger object to log cat vote
            logger.warning(f'{button1} Vote', extra=properties)

            vote2 = r.get(button2).decode('utf-8')
            properties = {'custom_dimensions': {'Dogs Vote': vote2}}
            # use logger object to log dog vote
            logger.warning(f'{button2} Vote', extra=properties)

            return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

        else:

            # Insert vote result into DB
            vote = request.form['vote']
            r.incr(vote,1)

            # Get current values
            vote1 = r.get(button1).decode('utf-8')
            vote2 = r.get(button2).decode('utf-8')

            # Return results
            return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

if __name__ == "__main__":
    # Use the statement below when running locally
    #app.run() 
    # Use the statement below before deployment to VMSS
    app.run(host='20.253.164.53', threaded=True, debug=True) # remote
