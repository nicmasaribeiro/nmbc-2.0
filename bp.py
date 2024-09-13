
from flask import Flask
from flask.views import MethodView
import marshmallow as ma
from flask_smorest import Api, Blueprint, abort
from models import app
import hashlib
import json
import time
import datetime as dt

app.config["API_TITLE"] = "My API"
app.config["API_VERSION"] = "v1"
app.config["OPENAPI_VERSION"] = "3.0.2"
api = Api(app)


f = open('/Users/nivmasagao/Desktop/tdbc-v3/app/portfolio/chain.json')
chain = json.load(f)
print(chain)

new_element = {
    "name": "btc",
    "personal_token": "b7d51360e3f546ac5d48",
    "transaction": [
        {
            "type": "buy",
            "coins": 10,
            "cash": 5
        }
    ]
}

#with open('portfolio/chain.json','a') as file:
#   json.dump(new_element, file,indent=4)

f = open('/Users/nivmasagao/Desktop/tdbc-v3/app/portfolio/chain.json')
chain = json.load(f)
print(chain)
#
#Bet = [
#   {'id': 0,'username': None ,'previous_hash':0000,
#       "transaction": [{'to':None,'from':None,'coins': 0,'cash': 0,'date':dt.date.today()}]
#   }]
#
##Bet.append(next_block)
##Bet.append(next_block2)
#

#print(data)
##print(Bet)
#
#import json
#
## Initial JSON structure
#chain = [
#   {
#       "name": "nmr",
#       "personal_token": "a3d51360e3f546ac5c36",
#       "transaction": [
#           {
#               "type": "close_position",
#               "coins": 50,
#               "cash": 10
#           }
#       ]
#   }
#]
#
## Adding a new transaction to the existing structure
#new_transaction = {
#   "type": "open_position",
#   "coins": 100,
#   "cash": 20
#}
#
## Assuming we want to add this new transaction to the first element in the chain
#chain[0]['transaction'].append(new_transaction)
#
## Adding a new element to the chain
#new_element = {
#   "name": "btc",
#   "personal_token": "b7d51360e3f546ac5d48",
#   "transaction": [
#       {
#           "type": "buy",
#           "coins": 10,
#           "cash": 5
#       }
#   ]
#}
#chain.append(new_element)
#
## Convert back to JSON string if needed
#chain_json = json.dumps(chain, indent=4)
#print(chain_json)
#
#
##new_db = json.load(f)
##json.dump(Bet,)
#
### Blockchain implementation
##class Blockchain:
#   def __init__(self):
#       self.chain = []
#       self.create_block(proof=1, previous_hash='0')
#
#   def create_block(self, proof, previous_hash):
#       block = {'index': len(self.chain) + 1,
#                'timestamp': time.time(),
#                'proof': proof,
#                'previous_hash': previous_hash,
#                'transactions': Bet.copy()}
#       self.chain.append(block)
#       return block
#
#   def get_previous_block(self):
#       return self.chain[-1]
#
#   def proof_of_work(self, previous_proof):
#       new_proof = 1
#       check_proof = False
#       while check_proof is False:
#           hash_operation = hashlib.sha256(str(new_proof**2 - previous_proof**2).encode()).hexdigest()
#           if hash_operation[:4] == '0000':
#               check_proof = True
#           else:
#               new_proof += 1
#       return new_proof
#
#    
#
#blockchain = Blockchain()
#
#blp_bets = Blueprint('bets', __name__)
#
#
#class BetQueryArgsSchema(ma.Schema):
#   name = ma.fields.String()
#
#class BetSchema(ma.Schema):
#   id = ma.fields.Int(dump_only=True)
#   username = ma.fields.String(required=True)
#   transaction = ma.fields.List(ma.fields.Dict(), required=True)
#
#def add_bet(new_data):
#   new_id = max(b['id'] for b in Bet) + 1 if Bet else 1
#   new_bet = {
#       'id': new_id,
#       'username': new_data['username'],
#       'transaction': new_data['transaction']
#   }
#   Bet.append(new_bet)
#   previous_block = blockchain.get_previous_block()
#   proof = blockchain.proof_of_work(previous_block['proof'])
#   previous_hash = blockchain.hash(previous_block)
#   blockchain.create_block(proof, previous_hash)
#   return new_bet
#
#@blp_bets.route("/")
#class Bets(MethodView):
#   @blp_bets.arguments(BetQueryArgsSchema, location="query")
#   @blp_bets.response(200, BetSchema(many=True))
#   def get(self, args):
#       """List bets"""
#       # Dummy filter function, replace with actual filter logic
#       filtered_bets = [bet for bet in Bet if bet['username'] == args.get('name', bet['username'])]
#       return filtered_bets
#
#   @blp_bets.arguments(BetSchema)
#   @blp_bets.response(201, BetSchema)
#   def post(self, new_data):
#       """Add a new bet"""
#       new_bet = add_bet(new_data)
#       return new_bet
#
#@blp_bets.route("/<bet_id>")
#class BetsById(MethodView):
#   @blp_bets.response(200, BetSchema)
#   def get(self, bet_id):
#       """Get bet by ID"""
#       bet = next((b for b in Bet if b['id'] == int(bet_id)), None)
#       if not bet:
#           abort(404, message="Bet not found.")
#       return bet
#
#   @blp_bets.arguments(BetSchema)
#   @blp_bets.response(200, BetSchema)
#   def put(self, update_data, bet_id):
#       """Update existing bet"""
#       bet = next((b for b in Bet if b['id'] == int(bet_id)), None)
#       if not bet:
#           abort(404, message="Bet not found.")
#       bet.update(update_data)
#       previous_block = blockchain.get_previous_block()
#       proof = blockchain.proof_of_work(previous_block['proof'])
#       previous_hash = blockchain.hash(previous_block)
#       blockchain.create_block(proof, previous_hash)
#       return bet
#
#   @blp_bets.response(204)
#   def delete(self, bet_id):
#       """Delete bet"""
#       global Bet
#       bet = next((b for b in Bet if b['id'] == int(bet_id)), None)
#       if not bet:
#           abort(404, message="Bet not found.")
#       Bet = [b for b in Bet if b['id'] != int(bet_id)]
#       return '', 204
#
#@blp_bets.route("/append_bet", methods=["POST"])
#class AppendBet(MethodView):
#   @blp_bets.arguments(BetSchema)
#   @blp_bets.response(201, BetSchema)
#   def post(self, new_data):
#       """Append a new bet"""
#       new_bet = add_bet(new_data)
#       return new_bet
#
#api.register_blueprint(blp_bets)/
