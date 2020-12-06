#!/usr/bin/env python3

from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import json
import traceback
import sys
from urllib.parse import unquote

"""
API:
/initialize/{BUDGET}
/add_team/{TEAM NAME}
/remove_team/{TEAM NAME}
/start auction/{PLAYER NAME}/{PLAYER POSITION}
/finish_auction/{TEAM NAME}/{DOLLAR AMOUNT}
/add_player/{TEAM NAME}/{PLAYER NAME}/{PLAYER POSITION}/{DOLLAR AMOUNT}
/remove_player/{PLAYER NAME}
"""

BUDGET = None
CURRENT_AUCTION = None
# team name -> Pair[SingletonList[Remaining dollars], List[(player name, player position, dollar amount)]]
TEAM_DATA = None


def initialize(args):
  global BUDGET
  global TEAM_DATA
  global CURRENT_AUCTION
  BUDGET = int(args[0])
  TEAM_DATA = {}
  CURRENT_AUCTION = None
  print("Initialized new draft with budget {}".format(BUDGET))
  return {}


def add_team(args):
  global BUDGET
  global TEAM_DATA
  team_name = args[0]
  if team_name in TEAM_DATA:
    raise Exception("Duplicate team name: {}".format(team_name))
  if BUDGET is None:
    raise Exception("Budget is not yet set")
  TEAM_DATA[team_name] = ([BUDGET], [])
  print("Added team {}. There are now {} teams.".format(team_name, len(TEAM_DATA)))
  return {}


def remove_team(args):
  global TEAM_DATA
  team_name = args[0]
  if team_name not in TEAM_DATA:
    raise Exception("Cannot remove team name: {}".format(team_name))
  del TEAM_DATA[team_name]
  print("Removed team {}. There are {} teams.".format(team_name, len(TEAM_DATA)))
  return {}


def start_auction(args):
  global CURRENT_AUCTION
  player_name = args[0]
  player_position = args[1]
  if CURRENT_AUCTION is not None:
    raise Exception("There is an active auction: {}".format(CURRENT_AUCTION))
  for team_name in TEAM_DATA.keys():
    for name, position, price in TEAM_DATA[team_name][1]:
      if name == player_name:
        raise Exception("Player has already been auctioned")
  CURRENT_AUCTION = (player_name, player_position)
  return {}


def finish_auction(args):
  global CURRENT_AUCTION
  global TEAM_DATA
  team_name = args[0]
  dollar_amount = int(args[1])
  if CURRENT_AUCTION is None:
    raise Exception("There is no active auction")
  player_name, player_position = CURRENT_AUCTION
  current_budget = TEAM_DATA[team_name][0][0]
  if dollar_amount > current_budget:
    raise Exception("Not enough money")
  TEAM_DATA[team_name][0][0] = current_budget - dollar_amount
  TEAM_DATA[team_name][1].append((player_name, player_position, dollar_amount))
  CURRENT_AUCTION = None
  return {}


def remove_player(args):
  player_name = args[0] 
  found = False
  for team_name in TEAM_DATA.keys():
    if found:
      break
    roster = TEAM_DATA[team_name][1]
    for i in range(len(roster)):
      if roster[i][0] == player_name:
        found = True
        dollar_amount = roster[i][2]
        print("Removing {} from {}".format(player_name, team_name))
        TEAM_DATA[team_name][1].pop(i)
        current_budget = TEAM_DATA[team_name][0][0]
        TEAM_DATA[team_name][0][0] = current_budget + dollar_amount
        break
  return {}


def get_state(args):
  result = {}
  if BUDGET is not None:
    result['total_budget'] = BUDGET
  if CURRENT_AUCTION is not None:
    result['current_auction'] = {}
    result['current_auction']['name'] = CURRENT_AUCTION[0]
    result['current_auction']['position'] = CURRENT_AUCTION[1]
  result['team_data'] = []
  if TEAM_DATA is not None:
    team_datas = []
    for team_name in TEAM_DATA.keys():
      team_data = {}
      team_data['name'] = team_name
      remaining_budget = TEAM_DATA[team_name][0][0]
      team_data['budget'] = remaining_budget
      players = []
      for (name, position, dollar_amount) in TEAM_DATA[team_name][1]:
        player = {}
        player['name'] = name
        player['position'] = position
        player['dollar_amount'] = dollar_amount
        players.append(player)
      team_data['players'] = players
      team_datas.append(team_data)
    result['team_data'] = team_datas
  return result



class Server(BaseHTTPRequestHandler):
  def do_GET(self):
    parts = unquote(self.path).split('/')[3:]
    if parts[0] != 'get_state':
      print("Received request: {}".format(self.path))
    dispatcher = {
      "initialize": lambda args: initialize(args),
      "add_team": lambda args: add_team(args),
      "remove_team": lambda args: remove_team(args),
      "start_auction": lambda args: start_auction(args),
      "finish_auction": lambda args: finish_auction(args),
      "remove_player": lambda args: remove_player(args),
      "get_state": lambda args: get_state(args),
    }
    try:
      response_dict = dispatcher[parts[0]](parts[1:])
      self.send_response(200)
      self.send_header("Content-type", "application/json")
      self.end_headers()
      self.wfile.write(json.dumps(response_dict).encode())
    except:
      trace = traceback.format_exc()
      print("Bad request. Exception: {}".format(trace))
      self.send_response(500)
      self.end_headers()
      self.wfile.write(trace.encode())
    sys.stdout.flush()
    sys.stderr.flush()


if __name__ == "__main__":
  host = "localhost"
  port = 8087
  server = HTTPServer((host, port), Server)
  print("Started http://{}:{}".format(host, port))
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    pass
  server.server_close()
  print("Shutting down")
