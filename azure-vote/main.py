from flask import Flask, request, render_template
import os
import random
import redis
import socket
import sys
import logging
from datetime import datetime

# App Insights
# Import required libraries for App Insights
from opencensus.trace.tracer import Tracer
from opencensus.trace import config_integration
from opencensus.ext.azure import metrics_exporter
from opencensus.stats import stats as stats_module
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.ext.flask.flask_middleware import FlaskMiddleware
from opencensus.ext.azure.log_exporter import AzureLogHandler, AzureEventHandler

# For metrics
stats = stats_module.stats
view_manager = stats.view_manager
config_integration.trace_integrations(["logging"])
config_integration.trace_integrations(["requests"])

# Logging
logger = logging.getLogger(__name__)
handler = AzureLogHandler(connection_string='InstrumentationKey=3948c691-9a6d-4560-a08a-648c94d9bf1e')
handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(handler)
# Add the event handler to the logger
logger.addHandler(AzureEventHandler(connection_string='InstrumentationKey=3948c691-9a6d-4560-a08a-648c94d9bf1e'))

# set logger level
logger.setLevel(logging.INFO)

# Metrics
exporter = metrics_exporter.new_metrics_exporter(
  enable_standard_metrics=True,
  connection_string='InstrumentationKey=3948c691-9a6d-4560-a08a-648c94d9bf1e')

# Tracing
tracer = Tracer(
    exporter=AzureExporter(
        connection_string='InstrumentationKey=3948c691-9a6d-4560-a08a-648c94d9bf1e'),
    sampler=ProbabilitySampler(1.0),
)

app = Flask(__name__)

# Requests
middleware = FlaskMiddleware(
    app,
    exporter=AzureExporter(connection_string="InstrumentationKey=3948c691-9a6d-4560-a08a-648c94d9bf1e"),
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
redis_server = os.environ['REDIS']
try:
    if "REDIS_PWD" in os.environ:
        r = redis.StrictRedis(host=redis_server,
                        port=6379,
                        password=os.environ['REDIS_PWD'])
    else:
        r = redis.Redis(redis_server)
    r.ping()
except redis.ConnectionError:
    exit('Failed to connect to Redis, terminating.')

# Change title to host name to demo NLB
if app.config['SHOWHOST'] == "true":
    title = socket.gethostname()

# Init Redis
if not r.get(button1): r.set(button1,0)
if not r.get(button2): r.set(button2,0)

@app.route('/', methods=['GET', 'POST'])
def index():
    print(f"Request Method: {request.method}")
    if request.method == 'GET':
        # Get current values
        vote1 = r.get(button1).decode('utf-8')
        # use tracer object to trace cat vote
        with tracer.span(name="Cats Vote") as span:
             logger.info("Cats Vote")

        print(f"Cats voted: {vote1}")

        vote2 = r.get(button2).decode('utf-8')
        # use tracer object to trace dog vote
        with tracer.span(name="Dogs Vote") as span:
            logger.info("Dogs Vote")

        print(f"Dogs voted: {vote2}")

        # Return index with values
        return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

    elif request.method == 'POST':

        if request.form['vote'] == 'reset':
            vote1 = r.get(button1).decode('utf-8')
            vote2 = r.get(button2).decode('utf-8')

            # Empty table and return results
            r.set(button1,0)
            r.set(button2,0)

            if vote1 > vote2:
                properties = {'custom_dimensions': {'Cats Vote': vote1}}
                # use logger object to log cat vote
                logger.info(f'{button1} Vote', extra=properties)
            elif vote1 < vote2:
                properties = {'custom_dimensions': {'Dogs Vote': vote2}}
                # use logger object to log dog vote
                logger.info(f'{button2} Vote', extra=properties)
            else:
                properties = {'custom_dimensions': {'Tie': vote1}}
                # use logger object to log tie
                logger.info(f'Tie', extra=properties)

            return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

        else:

            # Insert vote result into DB
            vote = request.form['vote']
            r.incr(vote,1)

            # Get current values
            vote1 = r.get(button1).decode('utf-8')
            properties = {"custom_dimensions": {"Cats Vote": vote1}}
            logger.info("Cats Vote", extra=properties)

            vote2 = r.get(button2).decode('utf-8')
            properties = {"custom_dimensions": {"Dogs Vote": vote2}}
            logger.info("Dogs Vote", extra=properties)

            # Return results
            return render_template("index.html", value1=int(vote1), value2=int(vote2), button1=button1, button2=button2, title=title)

if __name__ == "__main__":
    # Use the statement below when running locally
    #app.run() 
    # Use the statement below before deployment to VMSS
    app.run(host='0.0.0.0', threaded=True, debug=True) # remote
