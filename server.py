#!/usr/bin/env python3

##########################################
# Imports
import argparse
import speedtest
import json
import datetime

import waitress
import flask

##########################################
# Variables

args = None
lastCompletedRun = None
interval = 30
cachedLastResult = {}
parsedLastResult = ""
app = flask.Flask("speedtest-exporter")

##########################################
# Argparsing

def parseArgs():
  global args
  global interval
  Log("Parsing arguments...")
  parser = argparse.ArgumentParser(description="Implements a server that exports speedtest results in a prometheus format")
  parser.add_argument('-stale-interval', type=int, help="The interval in minutes after which a test becomes stale and needs to be rerun", default=30)
  parser.add_argument('-port', type=int, help="The port to listen on, defaults to 5000", default=9497)
  parser.add_argument('-log-level', type=str, help="The logging level for the application", choices=["critical", "error", "warning", "info", "debug", "trace"], default="info")
  parser.add_argument('-threads', type=str, help="The number of threads to use during the test, defaults to the number of threads provided by speedtest.net", default=None)
  parser.add_argument('-v', '-verbose', action="store_true", help="Turn on verbose output")
  parser.add_argument('-skip-bootstrap-test', action="store_true", help="Skip the initial bootstrapping speedtest")
  args = parser.parse_args()
  interval = datetime.timedelta(minutes=args.stale_interval)

##########################################
# Operations

def Log(message, quit:bool=False, quitWithStatus:int=1):
  if type(message) is dict:
    print(f'<{TimeStamp()}> - ' + "\n => ".join([k + ": " + str(message[k]) for k in message]))
  else:
    print(f'<{TimeStamp()}> - {message}')

  if quit or quitWithStatus > 1:
    exit(1 * quitWithStatus)

def TimeStamp():
  return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")

def RunTest():
  global lastCompletedRun
  global cachedLastResult
  n = datetime.datetime.now(datetime.timezone.utc)
  if lastCompletedRun != None and (lastCompletedRun + interval > n):
    if args.v:
      Log('VERBOSE: Skipping test run, last results are still fresh')
    return
  if args.v:
    Log('VERBOSE: Running test...')
  try:
    s = speedtest.Speedtest()
    s.get_servers()
    s.get_best_server()
    s.download(threads=args.threads)
    s.upload(threads=args.threads)

    lastCompletedRun = n
    cachedLastResult = s.results.dict()
    ParseMetrics()
  except Exception as e:
    Log("Last test run failed with error:")
    print(e)

def ParseMetrics():
  global cachedLastResult
  lines = []
  lines = lines + GenLines('speedtest_timestamp', 'Unix timestamp for the last run.', datetime.datetime.strptime(cachedLastResult['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.timezone.utc).timestamp())
  lines = lines + GenLines('speedtest_ping', 'Ping to testing server in ms', cachedLastResult['ping'])
  lines = lines + GenLines('speedtest_download_bytes_per_second', 'Download speed in bytes/second', cachedLastResult['download'])
  lines = lines + GenLines('speedtest_download_bytes', 'Total bytes downloaded', cachedLastResult['bytes_received'])
  lines = lines + GenLines('speedtest_upload_bytes_per_second', 'Upload speed in bytes/second', cachedLastResult['upload'])
  lines = lines + GenLines('speedtest_upload_bytes', 'Total bytes uploaded', cachedLastResult['bytes_sent'])
  lines = lines + GenLines('isp_rating', 'The rating of your ISP', cachedLastResult['client']['isprating'])
  global parsedLastResult
  parsedLastResult = '\n'.join(lines)
  if args.v:
    Log('VERBOSE: Successfully parsed metrics!')
    print(json.dumps(cachedLastResult, indent=2))

def GenLines(metricName:str, description:str, value:str):
  return [
    f'# HELP {metricName} {description}',
    f'# TYPE {metricName} gauge',
    f'{metricName}{{interval="{args.stale_interval}",from="SpeedtestExporter"}} {value}'
  ]

##########################################
# Routing
@app.get("/")
def rIndex():
  if args.v:
    Log(f'VERBOSE: Responding to {flask.request.remote_addr} with /')
  r = flask.Response()
  r.headers['Content-Type'] = "text/html"
  r.data = '''<!DOCTYPE HTML>
<HTML>
<HEAD>
  <title>SpeedTest Exporter</title>
</HEAD>
<BODY>
  <h1>SpeedTest Exporter</h1>
  <p><a href="metrics">Metrics</a></p>
</BODY>
</HTML>'''
  return r

@app.get("/metrics")
def rMetrics():
  if args.v:
    Log(f'VERBOSE: Responding to {flask.request.remote_addr} with /metrics')
  RunTest()
  r = flask.Response()
  r.headers['Content-Type'] = "text/plain"
  r.data = parsedLastResult
  return r

@app.get("/json")
def rJson():
  if args.v:
    Log(f'VERBOSE: Responding to {flask.request.remote_addr} with /json')
  r = flask.Response()
  r.headers['Content-Type'] = "application/json"
  r.data = json.dumps(cachedLastResult, indent=2)
  return r

##########################################
# Main

if __name__ == "__main__":
  Log("Starting main application...")
  parseArgs()
  if not args.skip_bootstrap_test:
    Log("Running initial bootstrap test...")
    RunTest()

  ##########################################
  # Running Server
  Log(f"Starting to listen on port {args.port}...")
  waitress.serve(app, port=args.port)