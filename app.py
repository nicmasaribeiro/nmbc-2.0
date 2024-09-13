from flask import Flask, render_template, request, redirect, abort, jsonify,sessions, Response, url_for,send_file,render_template_string
from flask import Blueprint
import os
import csv
import random
import xml.etree.ElementTree as ET
import xml.dom.minidom
import yfinance
import pandas as pd
import numpy as np
from bokeh.plotting import figure, output_file, save
from bokeh.embed import file_html
from bokeh.resources import CDN
from geom_forecast import GeometricBrownianMotion
import matplotlib.pyplot as plt
import datetime as dt
import base64
from bs import black_scholes
import requests
from models import *
from sqlalchemy import create_engine
from cryptography.hazmat.primitives.asymmetric import rsa as _rsa
from cryptography.hazmat.primitives import serialization
from sqlalchemy.orm import sessionmaker
from werkzeug.utils import secure_filename
from sqlalchemy import delete
import json
import yfinance as yf
import stripe
from flask_login import current_user, login_required, login_user
import time
from hashlib import sha256
from bc import * 


stripe.api_key = 'sk_test_51OncNPGfeF8U30tWYUqTL51OKfcRGuQVSgu0SXoecbNiYEV70bb409fP1wrYE6QpabFvQvuUyBseQC8ZhcS17Lob003x8cr2BQ'

investments = {'ticker':[],'price':[],'owner':[],'tokenized_price':[]}
clients = []
validators = []
pending = []
Bet = [{'id': 0,'username': None ,"transaction": [{'to':None,'from':None,'coins': 0,'cash': 0,'date':dt.date.today()}]}]

global coin
coin = Coin()
global blockchain
blockchain = Blockchain()
blockchain.create_genesis_block()
global network
network = Network()
network.create_genesis_block()

def update():
	invests = InvestmentDatabase.query.all()
	for i in invests:
		t = yf.Ticker(i.investment_name.upper())
		price = t.history(period='1d',interval='1m')['Close'][-1]
		change = (price - i.starting_price)/i.starting_price
		i.change_value = change
		db.session.commit()
		i.market_price = price
		db.session.commit()
		i.update_token_value()
	return 0

@login_manager.user_loader
def load_user(user_id):
	update()
	coin_db = CoinDB()
	db.session.add(coin_db)
	db.session.commit()
	betting_house = BettingHouse()
	db.session.add(betting_house)
	db.session.commit()
	return Users.query.get(int(user_id))

@app.route('/house')
def house():
	bet = BettingHouse.query.get_or_404(1)
	ls = {'coins':bet.coins,'cash':bet.balance}
	return jsonify(ls)

@app.route('/coin')
def coin_db():
	coin_db = CoinDB.query.get_or_404(1)
	ls = {'market_cap':coin_db.market_cap,
		 'staked_coins':coin_db.staked_coins,
		 'new_coins':coin_db.new_coins,
		 'dollar_value': coin_db.dollar_value,
		 'total_coins': coin_db.total_coins}
	return jsonify(ls)


@app.route('/buy/cash', methods=['GET'])
@login_required
def buy_cash():
	return render_template('stripe-payment.html')


@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
	try:
		user_id = current_user.id  # Assuming you're using Flask-Login
		
		checkout_session = stripe.checkout.Session.create(
			payment_method_types=['card'],
			line_items=[{
				'price_data': {
					'currency': 'usd',
					'product_data': {
						'name': 'Purchase Cash',
					},
					'unit_amount': 5000,  # Amount in cents ($50.00)
				},
				'quantity': 1,
			}],
			mode='payment',
			success_url=url_for('success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
			cancel_url=url_for('cancel', _external=True),
			metadata={
				'user_id': user_id  # Store user_id in the metadata
			}
		)
		return redirect(checkout_session.url, code=303)
	except Exception as e:
		return jsonify(error=str(e)), 403
	
@app.route('/success')
def success():
	session_id = request.args.get('session_id')
	session = stripe.checkout.Session.retrieve(session_id)
	if session.payment_status == 'paid':
		user_id = session.metadata['user_id']  # Retrieve user_id from metadata
		user = Users.query.get_or_404(user_id)
		user_balance = Wallet.query.filter_by(address=user.username).first()
		user_balance.balance += 50  # Adding $50 to user's balance, modify as needed
		db.session.commit()
		pay_id =  session.payment_intent
		user.payment_id = pay_id
		db.session.commit()
		return f'<h1>Payment Successful</h1><a href="/">Home</a><h3>{pay_id}</h3>'
	else:
		return '<h1>Payment Failed</h1><a href="/">Home</a>'
	
@app.route('/cancel')
def cancel():
	return '<h1>Payment Cancelled</h1><a href="/">Home</a>'

@app.route('/sell/cash', methods=['GET', 'POST'])
@login_required
def sell_cash():
	if request.method == 'POST':
		amount = request.form['amount']
		user_id = current_user.id  # Assuming you're using Flask-Login
		user = Users.query.get(user_id)
		user_balance = Wallet.query.filter_by(address=user.username).first()
		
		if user_balance.balance >= float(amount):
			# Deduct the balance from the user's wallet
			user_balance.balance -= float(amount)
			db.session.commit()
			
			# Create a refund in Stripe
			try:
				# You need to keep track of the payment intent ID during the payment process
				payment_intent_id = request.form['payment_intent_id']  # You'll need to pass this from the frontend
				refund = stripe.Refund.create(
					payment_intent=payment_intent_id,
					amount=int(float(amount) * 100),  # amount in cents
				)
				return jsonify({'message': 'Refund Successful', 'refund': refund}), 200
			except Exception as e:
				return jsonify(error=str(e)), 403
		else:
			return jsonify({'message': 'Insufficient Balance'}), 400
	return render_template('sell-cash.html')

@app.route('/')
def base():
	return render_template('base.html')

@app.route('/signup', methods=['POST','GET'])
def signup():
	if request.method =="POST":
		password = request.values.get("password")
		username = request.values.get("username")
		email = request.values.get("email")
		hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
		new_user = Users(username=username, email=email, password=hashed_password,personal_token=os.urandom(10).hex(),private_token=os.urandom(10).hex())
		db.session.add(new_user)
		db.session.commit()
		return jsonify({'message': 'User created!'}), 201
	return render_template("signup.html")

@app.route('/signup/wallet', methods=['POST','GET'])
def create_wallet():
	if request.method =="POST":
		username = request.values.get("username")
		password = request.values.get("password")
		users = Users.query.all()
		ls = [user.username for user in users]
		passwords = [user.username for user in users]
		if username in ls:
			if password in passwords:
				new_wallet = Wallet(address=username,token=username,password=password)
				db.session.add(new_wallet)
				db.session.commit()
				return jsonify({'message': 'Wallet Created!'}), 201
	return render_template("signup-wallet.html")

@app.route('/login', methods=['POST','GET'])
def login():
	if request.method == "POST":
		username = request.values.get("username")
		password = request.values.get("password")
		user = Users.query.filter_by(username=username).first()
		if user and bcrypt.check_password_hash(user.password, password):
			login_user(user)
			return redirect('/')
		else:
			return redirect('/signup')
	return render_template("login.html")

@app.route('/get/users', methods=['GET'])
@login_required
def get_users():
#	new_transaction = TransactionDatabase()
	users = Users.query.all()
	users_list = [{'id': user.id, 'username': user.username, 'email': user.email,'publicKey':str(user.personal_token)} for user in users]
	return jsonify(users_list)

@app.route('/signup/val', methods=['POST','GET'])
def signup_val():
	if request.method =="POST":
		password = request.values.get("password")
		username = request.values.get("username")
		users = Users.query.all()
		ls = [user.username for user in users]
		if username in ls:
			email = request.values.get("email")
			pk = str(os.urandom(10).hex())
			hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
			new_val = Peer(user_address=username, email=email, password=hashed_password,pk=pk)
			db.session.add(new_val)
			db.session.commit()
			return jsonify({'message': 'Val created!'}), 201
		else:
			pass
	return render_template("signup-val.html")

@app.route('/get/vals')
def get_vals():
	peers = Peer.query.all()
	peers_list = [{'id': peer.id, 'username': peer.user_address, 'email': peer.email,'public_key':str(peer.pk)} for peer in peers]
	return jsonify(peers_list) #render_template('validators.html', vals=validators)

@app.route('/peer/<address>/<password>', methods=['GET'])
def get_peer(address,password):
	user = Peer.query.filter_by(user_address=address).first()
	if user and bcrypt.check_password_hash(user.password, password):
		return jsonify({'id': user.id,'coins':user.miner_wallet,'cash':user.cash})
	else:
		return "Wrong Password"

@app.route('/usercred', methods=["GET","POST"])
def user_cred():
	if request.method == "POST":
		user = request.values.get("cred")
		password = request.values.get("password")
		return redirect(f'/users/{user}/{password}')
	return render_template('user-cred.html')

@app.route('/valcred', methods=["GET","POST"])
def val_cred():
	if request.method == "POST":
		user = request.values.get("username")
		password = request.values.get("password")
		peer = Peer.query.filter_by(user_address=user).first()
		ls = {'id':peer.id,'user_address':peer.user_address,'coins':peer.miner_wallet,'cash':peer.cash}
		return jsonify(ls) 
	return render_template('val-cred.html')

@app.route('/my/transactions',methods=['GET','POST'])
def my_trans():
	if request.method == "POST":
		username = request.values.get('username')
		trans = TransactionDatabase.query.filter_by(username=username).all()
		ls = [{'name':t.username,'amount':t.amount,'type':str(t.type),'from_address':t.from_address,'to_address':t.to_address,'txid':t.txid} for t in trans]
		return jsonify(ls)
	return render_template("mytans.html")

@app.route('/html/my/transactions',methods=['GET','POST'])
def my_html_trans():
	if request.method == "POST":
		username = request.values.get('username')
		trans = TransactionDatabase.query.filter_by(username=username).all()
		return render_template("view_trans.html",trans=trans)
	return render_template("mytans.html")
		
@app.route('/users/<user>/<password>', methods=['GET'])
def get_user(user,password):
	user = Users.query.filter_by(username=user).first()
	if user and bcrypt.check_password_hash(user.password, password):
		return jsonify({'id': user.id, 'username': user.username, 'email': user.email,'private_key':str(user.private_token),'personal_token':str(user.personal_token),'payment_id':user.payment_id})
	else:
		return redirect('/')


@app.route('/transact',methods=['GET','POST'])
@login_required
def create_transact():
	if request.method == "POST":
		id_from = request.values.get("username_from")
		id_to = request.values.get("username_to")
		value = .9*float(request.values.get("value"))
		stake = coin.process_coins()
		password = request.values.get("password")
		user = Users.query.filter_by(username=id_from).first()
		user2 = Users.query.filter_by(username=id_to).first()
		w1 = Wallet.query.filter_by(address=id_from).first()
		w2 = Wallet.query.filter_by(address=id_to).first()
		packet = str({'from':id_from,'to':id_to,'value':value}).encode()
		blockchain.add_transaction(packet.hex())
		pending = PendingTransactionDatabase(
									   txid=os.urandom(10).hex(),
									   username=w1.address,
									   from_address=w1.address,
									   to_address=w2.address,
									   amount=value,
									   timestamp=dt.datetime.now(),
									   type='internal_wallet',
									   signature=str(w1.address).encode().hex())
		db.session.add(pending)
		db.session.commit()
		from_addrs = user.username
		to_addrs = user2.username
		txid = str(os.urandom(10).hex())
		transaction = {
				 'index': len(blockchain.pending_transactions)+1,
				 'previous_hash': sha512(str(blockchain.get_latest_block()).encode()).hexdigest(),
				 'timestamp':dt.date.today(),
				 'transactions': blockchain.pending_transactions,
				 'hash':sha256(str(blockchain.pending_transactions).encode())}
		blockchain.receipts['to'] = user2.username
		blockchain.receipts['from'] = user.username
		blockchain.receipts['value'] = value
		blockchain.receipts['txid'] = txid
		network.add_transaction(blockchain.pending_transactions)
		blockchain.add_transaction(transaction)
		blockchain.money.append(value)
		if user and bcrypt.check_password_hash(user.password, password):
			betting_house = BettingHouse.query.get_or_404(1)
			betting_house.cash_fee(.1*value)			
			new_value = 0.9*value
			w1.set_transaction(w2, new_value)
			new_transaction = TransactionDatabase(
										 username=user.username,
										 txid=txid,
										 from_address = from_addrs,
										 signature=os.urandom(10).hex(),
										 to_address = to_addrs,
										 amount = value, 
										 type='send')
			db.session.add(new_transaction)
			db.session.commit()
			coin_db = CoinDB.query.get_or_404(1)
			# coin_db.gas(blockchain,6)
			return  """<a href='/'><h1>Home</h1></a><h3>Success</h3>"""
	
	return render_template("trans.html")


@app.route('/liquidate', methods=["POST","GET"])
def liquidate_asset():
	if request.method == 'POST':
		address = request.values.get('address')
		user = request.values.get('user')
		password = request.values.get('password')
		user_db = Users.query.filter_by(username=user).first()
		wal = Wallet.query.filter_by(address=user).first()
		transaction = TransactionDatabase.query.filter_by(from_address=user_db.personal_token).first()
		asset = InvestmentDatabase.query.filter_by(receipt=address).first()
		if asset.investors == 1:
			if password == asset.password and user == asset.owner:
				coin_db = CoinDB.query.get_or_404(1)
				sell_price = asset.market_cap
				wal.coins += sell_price
				db.session.commit()
				db.session.delete(asset)
				db.session.commit()
				return f"""<a href='/'><h1>Home</h1></a><h3>Successfully Liquidated Asset...{sell_price}</h3>"""
			else:
				pass
		else:
			return "<h1>Can't close position</h1>"
	return render_template("close_asset.html")

@app.route('/get/tokens', methods=["POST","GET"])
def get_asset_token():
	asset_tokens = AssetToken.query.all()
	ls = [{'id':asset.id,
		'token_address':asset.token_address,
		'user_address':asset.user_address,
		'transaction_receipt':asset.transaction_receipt,
		'username':asset.username,
		'coins':asset.coins} for asset in asset_tokens]
	return jsonify(ls)

@app.route('/make/block')
def make_block():
	if not blockchain:
		return "<h3>Blockchain instance not found</h3>"
	index = len(blockchain.chain) + 1
	previous_block = blockchain.get_latest_block()
	previous_hash = (str(blockchain.get_latest_block()).encode().hex())#if previous_block else '0'
	timestamp = dt.date.today()
	transactions = blockchain.pending_transactions
	index = len(network.chain) + 1
	previous_block = network.get_latest_block()
	previous_hash = (str(network.get_latest_block()).encode()).hex()#if previous_block else '0'
	timestamp = dt.datetime.now()
	transactions = blockchain.pending_transactions
	# Create a new block
	block_data = {
		'index': index,
		'previous_hash': previous_hash,
		'timestamp': timestamp,
		'transactions': transactions,
	}
	
	# Calculate the block hash
	block_string = str(block_data).encode()
	block_hash = hashlib.sha256(block_string).hexdigest()
	# Create the PrivateBlock and Block instances
	block = PrivateBlock(index, 
					  previous_hash, 
					  timestamp,
					  str(transactions),
					  block_hash)
	new_block = Block(
		index=int(index),
		previous_hash=str(previous_hash),
		timestamp=timestamp,
		transactions=str(transactions).encode(),
		hash=str(block_hash)
	)
	db.session.add(new_block)
	db.session.commit()
	blockchain.add_block(block)
	blockchain.approved_transactions.append(transactions)
	coin_db = CoinDB.query.get_or_404(1)
	coin_db.gas(blockchain,4)
	staked_coins = coin_db.proccess_coins(blockchain)
	t = blockchain.staked_coins.append(staked_coins)
	return f"""<a href='/'><h1>Home</h1></a><h3>Success</h3>{str(new_block).encode().decode()}"""

@login_required
@app.route('/cmc',methods=['GET'])
def cmc():
	user = current_user
	return render_template("cmc.html",user=user)

@login_required
@app.route('/html/trans',methods=['GET'])
def html_trans_database():
	t = TransactionDatabase.query.all()
	return render_template("html-trans.html", trans=t)

@login_required
@app.route('/html/investment/ledger',methods=['GET'])
def html_investment_ledger():
	t = InvestmentDatabase.query.all()
	return render_template("html-invest-ledger.html", invs=t)

@app.route('/get/approved',methods=['GET'])
def get_approved():
	trans =  Chain.query.all()
	ls = [{'id':t.id,'txid':t.txid,'username':t.username,'from':t.from_address,
		'to':t.to_address,'amount':t.amount,'time':t.timestamp,'type':str(t.type),'signature':t.signature} for t in trans]
	return jsonify(ls)

@app.route('/get/blocks',methods=['GET'])
def get_blocks():
	transports = Block.query.all()
	transports_list = [{'id': t.id,'index':str(t.index),'transactions':str(t.transactions)} for t in transports]
	return jsonify(transports_list)

@app.route('/get/block/<int:id>',methods=['GET'])
@login_required
def html_block(id):
	block = Block.query.get_or_404(id)
	return jsonify({'transactions':str(block.transactions),'id':block.id})

@app.route('/html/block/<int:id>',methods=['GET'])
@login_required
def get_block(id):
	block = Block.query.get_or_404(id)
	return render_template("html-block.html",block=block)


@app.route('/get/mywallet', methods=['GET'])
@login_required
def get_user_wallet():
	user = current_user
	
	# Fetch the user's wallet
	wallet = Wallet.query.filter_by(address=user.username).first()
	
	if not wallet:
		return "Wallet not found", 404
	
	# Fetch all asset tokens for the user
	assets = AssetToken.query.filter_by(username=user.username).all()
	
	# Initialize the dataframe dictionary
	df = {
		'inv_name': [], 
		'quantity': [], 
		'marketcap': [], 
		'starting_price': [], 
		'market_price': [], 
		'coins_value': [], 
		'change_value': []
	}
	
	for asset in assets:
		invs = InvestmentDatabase.query.filter_by(receipt=asset.transaction_receipt).first()
		print(invs)
		if invs:
			update()
			df['inv_name'].append(invs.investment_name)
			df['quantity'].append(invs.quantity)
			df['marketcap'].append(invs.market_cap)
			df['starting_price'].append(invs.starting_price)
			df['market_price'].append(invs.market_price)
			df['coins_value'].append(invs.coins_value)
			df['change_value'].append(invs.change_value)
    
    # Convert the dictionary to a pandas DataFrame
	dataframe = pd.DataFrame(df)
    
    # Transport list for potential future JSON response
	transports_list = [{"address": wallet.address, "balance": wallet.balance, "coins": wallet.coins}]
    
		# Convert DataFrame to HTML table with styles
	html = dataframe.to_html(index=False)
	html_table_with_styles = f"""
		<style>
			table {{
				width: 100%;
				border-collapse: collapse;
			}}
			th, td {{
				border: 1px solid black;
				padding: 10px;
				text-align: left;
			}}
			th {{
				background-color: #f2f2f2;
			}}
			tr:nth-child(even) {{
				background-color: #f9f9f9;
			}}
		</style>
		<h1><a href="/cmc">Back</a></h1>
		{html}
	"""
	
	# Render the HTML table as a response
	return render_template_string(html_table_with_styles)

@app.route('/html/mywallet',methods=['GET'])
@login_required
def html_wallet():
	user = current_user
	wallet = Wallet.query.filter_by(address=user.username).first()
	return render_template("mywallet.html",wallet=wallet)


@app.route('/bc/receipts',methods=['GET'])
@login_required
def get_bc_receipts():
	df = pd.DataFrame(blockchain.receipts)
	return df.to_html()


@app.route('/get/trans/<int:id>',methods=['GET'])
@login_required
def get_transaction(id):
	t = TransactionDatabase.query.get_or_404(id)
	transports_list = [{'user':t.username,'id': t.id, 'from_address':str(t.from_address),'to_address':str(t.to_address),'value':t.amount,'txid':t.txid}]
	return jsonify(transports_list)


@app.route('/get/block/<int:id>',methods=['GET'])
@login_required
def get_block_id(id):
	t = TransactionDatabase.query.get_or_404(id)
	transports_list = [{'user':t.username,'id': t.id, 'from_address':str(t.from_address),'to_address':str(t.to_address),'value':t.amount,'txid':t.txid}]
	return jsonify(transports_list)


@app.route('/get/ledger',methods=['GET'])
@login_required
def get_ledger():
	trans = TransactionDatabase.query.all()
	transports_list = [{'user':t.username,'id': t.id,'type':str(t.type), 'from_address':str(t.from_address),'to_address':str(t.to_address),'value':t.amount,'txid':t.txid} for t in trans]
	return jsonify(transports_list)


@app.route('/get/wallets',methods=['GET'])
@login_required
def get_wallets():
	transports = Wallet.query.all()
	transports_list = [{'address':t.address,'id':t.id,'user':str(t.token)} for t in transports]
	return jsonify(transports_list)

@app.route("/validate/hash",methods=['GET',"POST"])
def validate():
	if request.method == "POST":
		plain = request.values.get("plain")
		hash_value = request.values.get("hash")
		if hash_value == sha512(str(plain).encode()).hexdigest():
			return f"<h1>Valid ID</h1><h2>{plain}</h2><h2>{hash_value}</h2>"
		else:
			return "<h1>Incorrect ID</h1>"
	return render_template("validate-hash.html")



@login_required
@app.route('/get/pending')
def get_pending():
	trans = PendingTransactionDatabase.query.all()
	ls = [{'id':t.id,'txid':t.txid,'username':t.username,'from':t.from_address,
		'to':t.to_address,'amount':t.amount,'time':t.timestamp,'type':str(t.type),'signature':t.signature} for t in trans]
	return jsonify(ls)

@app.route('/show')
def show():
	csv = pd.read_csv("portfolio/pending.csv")
	html = csv.to_html()
	return f"""<h1><a href='/'>Database</a></h1>{html}"""

@app.route('/mine', methods=['GET', 'POST'])
def mine():
	if request.method == 'POST':
		blockdata = Block.query.all()
		user_address = request.values.get("user_address")
		miner = Peer.query.filter_by(user_address=user_address).first()
		n = network.get_stake()
		staked_coins = [10] # Initialize with the first stake value as an integer
		coin_db = CoinDB.query.get_or_404(1)
		for i in blockdata:
			status = blockchain.is_chain_valid()
			s_status = network.is_chain_valid()
			print('\nthe status is\n', status)
			print('\nthe status is\n', s_status)
			pending_transactions = PendingTransactionDatabase.query.all()
			for i in pending_transactions:
				approved_transaction = Chain(txid=i.txid,
								  username=i.username,
								  from_address=i.from_address,
								  to_address=i.to_address,
								  amount=i.amount,
								  timestamp=i.timestamp,
								  type=i.type,
								  signature=i.signature)
				db.session.add(approved_transaction)
				db.session.commit()
			nonce, hash_result, time_taken = blockchain.proof_of_work(i, 5)
			nonce, hash_result, time_taken = network.proof_of_work(i, 5)
			staked_proccess = coin.process_coins()
			coin_db.gas(blockchain,10)
			all_approved_transactions = Chain.query.all()
			approved_values = [i.amount for i in all_approved_transactions]
			amount_values = [i.amount for i in pending_transactions]
			print(amount_values)
			stake = coin.stake_coins(approved_values,amount_values)
			coin_db.staked_coins+=stake
			db.session.commit()
			blockchain.market_cap += stake # + staked_proccess
			staked_coins.append(stake) #+ 
			staked_coins.append(coin_db.new_coins)# .market_cap # Add the stake value to the total
			blockchain.mine_pending_transactions(1)
			value = sum(staked_coins)/len(staked_coins)
			for i in pending_transactions:
				db.session.delete(i)
				db.session.commit()
			staked_coins = []
		miner.miner_wallet+=value
		db.session.commit()
		return f"<h1><a href='/'> Home </a></h1><h3>Success</h3>You've mined {value} coins"
	return render_template('mine.html')


@app.route('/create/investment', methods=['GET', 'POST'])
def buy_or_sell():
	update()
	if request.method == "POST":
		user = request.values.get('name')
		invest_name = request.values.get('ticker').upper()
		coins = float(request.values.get('coins'))
		password = request.values.get('password')
		qt = float(request.values.get("qt"))
		user_db = Users.query.filter_by(username=user).first()
		
		if not user_db:
			return "<h3>User not found</h3>"
		
		ticker = yf.Ticker(invest_name)
		history = ticker.history(period='1d', interval='1m')
		
		if history.empty:
			return "<h3>Invalid ticker symbol</h3>"
		
		price = history['Close'][-1]
		token_price = price * qt / coins
		
		wal = Wallet.query.filter_by(address=user).first()
		if wal and wal.coins >= coins:
			receipt = os.urandom(10).hex()
			new_transaction = TransactionDatabase(
				txid=receipt,
				from_address=user_db.personal_token,
				to_address=invest_name,
				amount=coins * qt,
				type='investment',
				username = user,
				signature=sha256(str(user_db.private_token).encode()).hexdigest()
			)
			db.session.add(new_transaction)
			db.session.commit()
			
			new_asset_token = AssetToken(
				username=user,
				token_address=receipt,
				user_address=user_db.personal_token,
				token_name = invest_name,
				transaction_receipt=os.urandom(10).hex(),
				quantity=qt,
				cash = qt * price,
				coins=coins
			)
			db.session.add(new_asset_token)
			db.session.commit()
			
			new_investment = InvestmentDatabase(
				owner=user,
				investment_name=invest_name,
				password=password,
				quantity=qt,
				market_cap=qt * price,
				starting_price=price,
				market_price=price,
				coins_value=coins,
				investors=1,
				receipt=receipt
			)
			db.session.add(new_investment)
			db.session.commit()
			wal.coins -= coins
			db.session.commit()
			# Create the block data
			pen_trans=PendingTransactionDatabase.query.all()[-1]
			all_pending = PendingTransactionDatabase.query.all()
			packet = {
				'index': len(blockchain.chain) + 1,
				'previous_hash': hash(str(blockchain.get_latest_block())),
				'datetime': str(dt.datetime.now()),
				'transactions': all_pending,
			}
			encoded_packet = str(packet).encode().hex()
		
			blockdata = Block(
				index = len(Block.query.all())+1,
				previous_hash=pen_trans.signature,
				timestamp=dt.datetime.now(),
				hash = encoded_packet,
				transactions = str(all_pending))
			
			db.session.add(blockdata)
			db.session.commit()
			blockchain.add_block(packet)
			return """<a href='/'><h1>Home</h1></a><h3>Success</h3>"""
		else:
			return "<h3>Insufficient coins in wallet</h3>"
	return render_template('make-investment-page.html')


@app.route('/track/inv', methods=['GET','POST'])
def track_invest():
	if request.method == 'POST':
		receipt = request.form.get('receipt')
		tracked = TrackInvestors.query.filter_by(receipt=receipt).all()
		ls = [{'id': t.id, 'receipt':t.receipt,
         'investor_name': t.investor_name, 
         'token': t.investor_token, 
         'investment_name': t.investment_name, 
         'owner': t.owner,
         'tokenized_price': t.tokenized_price} for t in tracked]
		return jsonify(ls)
	return render_template("inv-inv.html")

@app.route('/search/<receipt>')
def search(receipt):
    asset = InvestmentDatabase.query.filter_by(receipt=receipt).first()
    return render_template('search.html',asset=asset)

@login_required
@app.route('/invest/asset',methods=['GET','POST'])
def invest():
	update()
	if request.method =="POST":
		user = request.values.get('name')
		receipt = request.values.get('address')
		staked_coins = float(request.values.get('amount'))
		password = request.values.get('password')
		user_name = Users.query.filter_by(username=user).first()
		inv = InvestmentDatabase.query.filter_by(receipt=receipt).first()
		wal = Wallet.query.filter_by(address=user_name.username).first()
		if password == wal.password:
			if wal.coins >= staked_coins:
				house = BettingHouse.query.get_or_404(1)
				house.coin_fee(0.1*staked_coins)
				new_value = 0.9*staked_coins
				wal.coins -= staked_coins
				inv.coins_value += staked_coins
				db.session.commit()
				new_transaction = TransactionDatabase(
        								  username=user,
                                          txid=inv.receipt,
                                          from_address=user_name.personal_token,
                                          to_address=inv.investment_name,
                                          amount=staked_coins,type='investment',
                                          signature=os.urandom(10).hex())
				db.session.add(new_transaction)
				db.session.commit()
				inv.add_investor()
				inv.append_investor_token(
        					  name=user, 
                              address=user_name.personal_token, 
                              receipt=inv.receipt,
                              amount=staked_coins,
                              currency='coins')
				a_tk = AssetToken(
        			 username=user,
                     token_name=inv.investment_name,
                     token_address=os.urandom(10).hex(),
                     user_address=user_name.personal_token,
                     transaction_receipt=inv.receipt,
                     quantity=staked_coins,
                     cash = coin.dollar_value*inv.tokenized_price,
                     coins = inv.tokenized_price)
				db.session.add(a_tk)
				db.session.commit()
				track = TrackInvestors(
        			 	   receipt=receipt,
                           tokenized_price=inv.tokenized_price,
                           owner = sha512(str(inv.owner).encode()).hexdigest(),
                           investment_name=inv.investment_name,
                           investor_name=sha512(str(user_name.username).encode()).hexdigest(),
                           investor_token=user_name.personal_token)
				db.session.add(track)
				db.session.commit()
				blockchain.add_transaction({
        					    'index':len(blockchain.chain)+1,
                                "previous_hash":str(blockchain.get_latest_block()).encode().hex(),
                                'timestamp':str(dt.date.today()),
                                'data':str({'receipt':receipt,
                                            'tokenized_price':inv.tokenized_price,
                                            'owner':inv.owner,
                                            'investment_name':inv.investment_name,
                                            'investor_name':user_name.username,
                                            'investor_token':user_name.personal_token})})
				return f"""<a href='/'><h1>Home</h1></a><h3>Success</h3><p>You've successfully invested {staked_coins} in {inv.investment_name}"""
			else:
				return "<h3>Insufficient coins in wallet</h3>"
	return render_template("invest-in-asset.html")

@app.route('/asset/info/<int:id>')
def info_assets(id):
	update()
	asset = InvestmentDatabase.query.get_or_404(id)
	return render_template("asset-info.html", asset=asset)\

@app.route('/get/asset/<int:id>',methods=['GET','POST'])
def get_asset(id):
	try:
		t = InvestmentDatabase.query.get_or_404(id)
		info = {'id': t.id,'name': str(t.investment_name),'owner':t.owner,'investors_num':t.investors,'market_cap':str(t.market_cap),'coins_value':str(t.coins_value),'receipt':str(t.receipt),'tokenized_price':str(t.tokenized_price),'market_price':t.market_price,'change':t.change_value,'original_price':t.starting_price}
		return jsonify(info)
	except:
		return "<h2>The asset is no longer active<h2>"

@app.route('/price',methods=['GET','POST'])
def price():
	if request.method =="POST":
		username = request.values.get('username')
		password = request.values.get('password')
		stake = float(request.values.get("stake"))
		S = float(request.form['S'])
		K = float(request.form['K'])
		T = float(request.form['T'])
		r = float(request.form['r'])
		sigma = float(request.form['sigma'])
		option_type = request.form['option_type']
		price = black_scholes(S, K, T, r, sigma)
		return f"{price}"
	return render_template("options-pricing.html")

@app.route('/buy/coins',methods=['GET','POST'])
def buy_coins():
	if request.method =="POST":
		exchange = 100
		value = float(request.values.get('value'))
		id = request.values.get('id')
		username = request.values.get('username')
		password = request.values.get('password')
		house = BettingHouse.query.get_or_404(1)
		user = Users.query.filter_by(username=username).first()
		wal = Wallet.query.filter_by(address=username).first()
		if user and bcrypt.check_password_hash(user.password, password):
			coins = float(value*exchange)
			if coins <= house.coins:
				house.coins -= coins
				db.session.commit()
				wal.balance -= value
				db.session.commit()
				wal.coins += coins
				db.session.commit()
		return """<a href='/'><h1>Home</h1></a><h3>Success</h3>"""
	return render_template("buycash.html")

@app.route('/sell/coins',methods=['GET','POST'])
def sell_coins():
	if request.method =="POST":
		exchange = coin.dollar_value
		value = float(request.values.get('value'))
		username = request.values.get('username')
		password = request.values.get('password')
		house = BettingHouse.query.get_or_404(1)
		user = Users.query.filter_by(username=username).first()
		wal = Wallet.query.filter_by(address=username).first()
		if user and bcrypt.check_password_hash(user.password, password):
			if wal.coins >= value:
				house.coins += .05*value
				db.session.commit()
				cash = float(value*exchange*.95)
				wal.balance += cash
				db.session.commit()
				wal.coins -= value
				db.session.commit()
		return f"""<a href='/'><h1>Home</h1></a><h3>Success</h3><p>You've successfully sold {value} coins.</p>"""
	return render_template("sell.html")

@app.route('/my/assets',methods=['GET','POST'])
def my_assets():
	if request.method == 'POST':
		user_address = request.values.get("address")
		asset_tokens = AssetToken.query.filter_by(username=user_address).all()
		ls = [{
			'id':asset.id,
			'username':asset.username,
			'token_name':asset.token_name,
			'token_address':asset.token_address,
			'user_address':asset.user_address,
		 	'transaction_receipt':asset.transaction_receipt,
			'quantity':asset.quantity,
			'coins':asset.coins,
		 	'cash':asset.cash} for asset in asset_tokens]
		return jsonify(ls)
	return render_template("myassets.html")

@app.route('/html/my/assets',methods=['GET','POST'])
def html_my_assets():
	if request.method == 'POST':
		user_address = request.values.get("address")
		asset_tokens = AssetToken.query.filter_by(username=user_address).all()
		ls = [{
		 'token_address':asset.token_address,
		 'transaction_receipt':asset.transaction_receipt,
		 'coins':asset.coins,
		 'cash':asset.cash} for asset in asset_tokens]
		return render_template("myassets-view.html",assets=asset_tokens)
	return render_template("myassets.html")
	
@app.route('/sell/asset',methods=['GET','POST'])
def sell_asset():
	update()
	if request.method =="POST":
		update()
		address = request.values.get('address')
		user = request.values.get('user')
		password = request.values.get('password')
		invest = InvestmentDatabase.query.filter_by(receipt=address).first()
		wal = Wallet.query.filter_by(address=user).first()
		user_db = Users.query.filter_by(username=user).first()
		user_token = user_db.personal_token 
		asset_token = AssetToken.query.filter_by(transaction_receipt = address).first()
		if (asset_token != None) and (invest.investors > 1) and (invest != None):
				update()
				close_position = ((1+invest.change_value)*asset_token.quantity)*invest.tokenized_price
				wal.coins += close_position
				invest.investors -= 1
				invest.coins_value -= close_position
				db.session.commit()
				invest.update_token_value()
				bc_trans = {
        		'receipt':asset_token.token_address,
                'from_address':'market',
                'to_address':user,
                'amount':close_position,
                'type':"liquidation"}
				blockchain.add_transaction(bc_trans)
				new_transaction = TransactionDatabase(username=user,
                                          txid=asset_token.token_address,
                                          from_address='market',
                                          to_address=user,
                                          amount=close_position,
                                          type="liquidation",
                                          signature=asset_token.transaction_receipt)
				db.session.add(new_transaction)
				db.session.commit()
				db.session.delete(asset_token)
				db.session.commit()
				return f"""<a href='/'><h1>Home</h1></a><h3>Success</h3><h3>You have earned...{close_position}</h3>"""
		else:
			return f"""<h1>Liquidation Not Possible</h1>"""
	return render_template("liquidate.html")


##################################################
# Quantitative Services #########################
##################################################

@app.route("/implied-vol",methods=["POST",'GET'])
def implied_vol():
	from vol import implied_volatility_option
	if request.method == "POST":
		market = float(request.values.get("market"))
		S = float(request.values.get("S"))
		K = float(request.values.get("K"))
		T = float(request.values.get("T"))
		r = float(request.values.get("r"))
		otype = request.form['option_type']
		iv = implied_volatility_option(S,K,T,r,market,otype)
		return f"""<h1><a href='/'>Back</a></h1><h2> IMPLIED VOL</h2><h3>{iv}</h3>"""
	return render_template("IV.html")

@app.route('/download/csv',methods=['GET','POST'])
def download_csv():
    if request.method == "POST":
        tickers = request.values.get("tickers").upper()
        tickers = tickers.replace(',', ' ')
        tickers = yf.Tickers(tickers)
        period = request.values.get("period")
        interval = request.values.get("interval")
        history = tickers.history(period=period,interval=interval)
        df = history["Close"]
        csv = df.to_csv('data.csv')
        return send_file('data.csv', mimetype='text/csv', download_name='data.csv',as_attachment=True)
    return render_template("download-csv.html") 


@app.route('/cov/prices',methods=['GET','POST'])
def cov_prices():
	if request.method == 'POST':
		tickers = request.values.get("tickers").upper()
		tickers = tickers.replace(',', ' ')
		tickers = yf.Tickers(tickers)
		history = tickers.history(start='2018-1-1',end=dt.date.today())
		df = history['Close']
		covaraince = df.cov()
		html = covaraince.to_html()
		return f"""<h1><a href='/'>Back</a></h1><h2> Covaraince Prices</h2>{html}"""
	return render_template("cov.html")

@app.route('/cov/returns',methods=['GET','POST'])
def cov_returns():
	if request.method == 'POST':
		tickers = request.values.get("tickers").upper()
		tickers = tickers.replace(',', ' ')
		tickers = yf.Tickers(tickers)
		history = tickers.history(start='2018-1-1',end=dt.date.today())
		df = history['Close'].pct_change()
		covaraince = df.cov()*np.sqrt(256)
		html = covaraince.to_html()
		return f"""<h1><a href='/'>Back</a></h1><h2>Annualized Covaraince Returns</h2>{html}"""
	return render_template("cov.html")

@app.route('/corr/returns',methods=['GET','POST'])
def corr_returns():
	if request.method == 'POST':
		tickers = request.values.get("tickers").upper()
		tickers = tickers.replace(',', ' ')
		tickers = yf.Tickers(tickers)
		history = tickers.history(start='2018-1-1',end=dt.date.today())
		df = history['Close'].pct_change()
		correlation = df.corr()#*np.sqrt(256)
		html = correlation.to_html()
		return f"""<h1><a href='/'>Back</a></h1><h2>Correlation Returns</h2>{html}"""
	return render_template("cov.html")

@app.route('/corr/prices',methods=['GET','POST'])
def corr_prices():
	if request.method == 'POST':
		tickers = request.values.get("tickers").upper()
		tickers = tickers.replace(',', ' ')
		tickers = yf.Tickers(tickers)
		history = tickers.history(start='2018-1-1',end=dt.date.today())
		df = history['Close']#.pct_change()
		correlation = df.corr()#*np.sqrt(256)
		html = correlation.to_html()
		return f"""<h1><a href='/'>Back</a></h1><h2>Correlation Prices</h2>{html}"""
	return render_template("cov.html")

@app.route('/graph', methods=['GET', 'POST'])
def graph():
	if request.method == 'POST':
		ticker = request.values.get("asset").upper()
		period = request.form.get("ttype")
		ticker_data = yf.Ticker(ticker)
		hist = ticker_data.history(period=period)['Close']
		# Create the Bokeh plot
		p = figure(title=f"{ticker} Closing Prices", x_axis_label='Date', y_axis_label='Price', x_axis_type='datetime')
		p.line(hist.index, hist.values, line_width=2)
		# Generate the HTML for the plot
		html = file_html(p, CDN, f"{ticker} Closing Prices")
		return html
	return render_template('graph.html')

@app.route('/graph/freq', methods=['GET', 'POST'])
def graph_day():
	if request.method == 'POST':
		ticker = request.values.get("asset").upper()
		period = request.form.get("ttype")
		ticker_data = yf.Ticker(ticker)
		hist = ticker_data.history(interval=period,period='1d')['Close']
		open = ticker_data.history(interval=period,period='1d')['Open']
		sma = hist.rolling(7).mean()
		# Create the Bokeh plot
		p = figure(title=f"{ticker} Closing Prices", x_axis_label='Date', y_axis_label='Price', x_axis_type='datetime')
		p.line(hist.index, hist.values, line_width=2)
		p.line(open.index, open.values, line_width=2,color='red')
		p.line(open.index, sma.values, line_width=2,color='green')
		# Generate the HTML for the plot
		html = file_html(p, CDN, f"{ticker} Closing Prices")
		return html
	return render_template('graph-high.html')

@app.route('/1m/forecast', methods=['GET', 'POST'])
def graph_forecast_1m():
	if request.method == 'POST':
		ticker = request.values.get("asset").upper()
		ticker_data = yf.Ticker(ticker)
#		ttype = request.form.get('')
		hist = ticker_data.history(interval='1d',period='1mo')['Close']
		initial_price = hist[-1]
		ret = hist.pct_change()[1:]
		drift = np.mean(ret)*np.sqrt(256)
		volatility = np.std(hist)#*np.sqrt(256)
		dt = 1/31
		T = 2
		price_paths = []
		for i in range(0, 100):
			price_paths.append(GeometricBrownianMotion(initial_price, drift, volatility, dt, T).prices)
		# Create the Bokeh plot
		p = figure(title=f"{ticker} Closing Prices", x_axis_label='Date', y_axis_label='Price', x_axis_type='datetime')
		p.line(np.linspace(0,len(price_paths[0])),price_paths[0], line_width=2)
		p.line(np.linspace(0,len(price_paths[0])),price_paths[1],line_width=2,color='red')
		p.line(np.linspace(0,len(price_paths[0])),price_paths[2],line_width=2,color='green')
		p.line(np.linspace(0,len(price_paths[0])),price_paths[3], line_width=2)
		p.line(np.linspace(0,len(price_paths[0])),price_paths[4],line_width=2,color='blue')
		p.line(np.linspace(0,len(price_paths[0])),price_paths[5],line_width=2,color ='yellow')
		p.line(np.linspace(0,len(price_paths[0])),price_paths[6], line_width=2)
		p.line(np.linspace(0,len(price_paths[0])),price_paths[7],line_width=2)
		p.line(np.linspace(0,len(price_paths[0])),price_paths[8],line_width=2)
		p.line(np.linspace(0,len(price_paths[0])),price_paths[9], line_width=2)
		html = file_html(p, CDN, f"{ticker} Closing Prices")
		return html
	return render_template('graph-forecast.html')

@app.route('/1d/forecast', methods=['GET', 'POST'])
def graph_forecast_1d():
	if request.method == 'POST':
		ticker = request.values.get("asset").upper()
		ticker_data = yf.Ticker(ticker)
		hist = ticker_data.history(interval='1m',period='1d')['Close']
		initial_price = hist[-1]
		ret = hist.pct_change()[1:]
		drift = np.mean(ret)*np.sqrt(256)
		volatility = np.std(hist)#*np.sqrt(256)
		dt = 1/7
		T = 2
		price_paths = []
		for i in range(0, 1000):
			price_paths.append(GeometricBrownianMotion(initial_price, drift, volatility, dt, T).prices)
		# Create the Bokeh plot
		p = figure(title=f"{ticker} Closing Prices", x_axis_label='Date', y_axis_label='Price', x_axis_type='datetime')
		p.line(np.linspace(0,len(price_paths[0])),price_paths[0], line_width=2)
		p.line(np.linspace(0,len(price_paths[0])),price_paths[1],line_width=2,color='red')
		p.line(np.linspace(0,len(price_paths[0])),price_paths[2],line_width=2,color='green')
		p.line(np.linspace(0,len(price_paths[0])),price_paths[3], line_width=2)
		p.line(np.linspace(0,len(price_paths[0])),price_paths[4],line_width=2,color='blue')
		p.line(np.linspace(0,len(price_paths[0])),price_paths[5],line_width=2,color ='yellow')
		p.line(np.linspace(0,len(price_paths[0])),price_paths[6], line_width=2)
		p.line(np.linspace(0,len(price_paths[0])),price_paths[7],line_width=2)
		p.line(np.linspace(0,len(price_paths[0])),price_paths[8],line_width=2)
		p.line(np.linspace(0,len(price_paths[0])),price_paths[9], line_width=2)
		html = file_html(p, CDN, f"{ticker} Closing Prices")
		return html
	return render_template('graph-forecast.html')

@app.route('/1y/forecast', methods=['GET', 'POST'])
def graph_forecast_1y():
	if request.method == 'POST':
		ticker = request.values.get("asset").upper()
		ticker_data = yf.Ticker(ticker)
		hist = ticker_data.history(interval='1d',period='1y')['Close']
		initial_price = hist[-1]
		ret = hist.pct_change()[1:]
		drift = np.mean(ret)*np.sqrt(256)
		volatility = np.std(hist)#*np.sqrt(256)
		dt = 1/256
		T = 2
		price_paths = []
		for i in range(0, 100):
			price_paths.append(GeometricBrownianMotion(initial_price, drift, volatility, dt, T).prices)
		# Create the Bokeh plot
		p = figure(title=f"{ticker} Closing Prices", x_axis_label='Date', y_axis_label='Price', x_axis_type='datetime')
		p.line(np.linspace(0,len(price_paths[0])),price_paths[0], line_width=2)
		p.line(np.linspace(0,len(price_paths[0])),price_paths[1],line_width=2,color='red')
		p.line(np.linspace(0,len(price_paths[0])),price_paths[2],line_width=2,color='green')
		p.line(np.linspace(0,len(price_paths[0])),price_paths[3], line_width=2)
		p.line(np.linspace(0,len(price_paths[0])),price_paths[4],line_width=2,color='blue')
		p.line(np.linspace(0,len(price_paths[0])),price_paths[5],line_width=2,color ='yellow')
		p.line(np.linspace(0,len(price_paths[0])),price_paths[6], line_width=2)
		p.line(np.linspace(0,len(price_paths[0])),price_paths[7],line_width=2)
		p.line(np.linspace(0,len(price_paths[0])),price_paths[8],line_width=2)
		p.line(np.linspace(0,len(price_paths[0])),price_paths[9], line_width=2)
		html = file_html(p, CDN, f"{ticker} Closing Prices")
		return html
	return render_template('graph-forecast.html')

@app.route("/tradeview/<asset>")
def tradeview(asset):
	return render_template("tradeview.html",ticker=asset.upper())

@app.route("/admix")
def admix():
	return render_template("admix.html")

@app.route("/stats")
def stats():
	return render_template("admix-two.html")

@app.route("/geombrow/pred",methods=['GET','POST'])
def geombrow_pred():
	ticker = yf.Ticker('AAPL')
	df = ticker.history(period = '1d', interval='1m')
	print(df)
	stock = df['Close']
	ret = stock.pct_change()[1:]
	paths = 50
	initial_price = stock[-1]
	drift = np.mean(ret)
	volatility = np.std(stock)*np.sqrt(420)#*np.sqrt(256)
	dt = 1/420
	T = 1
	price_paths = []
	for i in range(0, paths):
		price_paths.append(GeometricBrownianMotion(initial_price, drift, volatility, dt, T).prices)
	return render_template('geombrow-pred.html',pr)

@app.route("/tree",methods=['GET','POST'])
def tree():
	if request.method == "POST":
		from tree import binomial_tree
		ticker = yf.Ticker('AAPL')
		df = ticker.history(period = '1d', interval='1m')['Close']
		initial_price = df[-1]
		S0 = float(request.values.get('s0')) # initial stock price
		u = float(request.values.get('u'))# up factor
		d = float(request.values.get('d'))# down factor
		p = float(request.values.get('p'))# probability of up move
		n = int(request.values.get('n'))   # number of steps
		tree = pd.DataFrame(binomial_tree(initial_price, u, d, p, n))
		html = tree.to_html()
		html_table_with_styles = f"""
		<style>
			table {{
				width: 100%;
				border-collapse: collapse;
			}}
			th, td {{
				border: 1px solid black;
				padding: 10px;
				text-align: left;
			}}
			th {{
				background-color: #f2f2f2;
			}}
			tr:nth-child(even) {{
				background-color: #f9f9f9;
			}}
		</style>
		<h1><a href="/cmc">Back</a></h1>
		<h2>Binomial Matrix Simulation</h2>
		{html}
		"""
		return html_table_with_styles
	return render_template("tree-view.html",style="color red;")

@app.route('/option/probdist',methods=["GET","POST"])
def prodist():
	import mpld3
	if request.method=="POST":
				# Black-Scholes parameters
		S0 = float(request.values.get("s0"))    # Initial stock price
		K = float(request.values.get("k"))     # Strike price
		T = float(request.values.get("t"))      # Time to maturity (in years)
		r = float(request.values.get("r"))   # Risk-free rate
		sigma = float(request.values.get("sigma")) # Volatility of the underlying asset
		n_sim = 100_000_000 # Number of simulations

		# Generate random numbers following a normal distribution for asset price simulation
		np.random.seed(42)
		Z = np.random.randn(n_sim)

		# Simulate stock price at maturity using Geometric Brownian Motion
		ST = S0 * np.exp((r - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * Z)

		# Calculate the payoff of the European call option
		payoff = np.maximum(ST - K, 0)

		# Calculate the discounted expected payoff (option price)
		option_price = np.exp(-r * T) * np.mean(payoff)

		hist, edges = np.histogram(ST, bins=100, density=True)
		p1 = figure(title=f"Simulated Stock Price Distribution at Maturity (T={T} year)",
				x_axis_label="Stock Price", y_axis_label="Probability Density")
		p1.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], fill_color="blue", line_color="white", alpha=0.75)
		# Save the stock price distribution plot to an HTML file
		html1 = file_html(p1, CDN)
		# # Plot the distribution of the option payoffs using Bokeh
		hist_payoff, edges_payoff = np.histogram(payoff, bins=100, density=True)
		p2 = figure(title="Distribution of Option Payoffs", 
					x_axis_label="Payoff", y_axis_label="Probability Density")
		p2.quad(top=hist_payoff, bottom=0, left=edges_payoff[:-1], right=edges_payoff[1:], fill_color="green", line_color="white", alpha=0.75)
		html2 = file_html(p2, CDN)
		return f"""{html1}<br>{html2}"""
	return render_template("probdist.html")

@app.route('/stats/binom',methods=['GET','POST'])
def stats_binom():
	from bin_stats_df import bin_stats_df#(ticker, period, interval)
	if request.method == "POST":
		t = request.values.get('ticker')
		p = request.values.get('perido')
		i = request.values.get('interval')
		df = bin_stats_df(t)
		html = df.to_html()
		html_table_with_styles = f"""
		<style>
			table {{
				width: 100%;
				border-collapse: collapse;
			}}
			th, td {{
				border: 1px solid black;
				padding: 10px;
				text-align: left;
			}}
			th {{
				background-color: #f2f2f2;
			}}
			tr:nth-child(even) {{
				background-color: #f9f9f9;
			}}
		</style>
		<h1><a href="/cmc">Back</a></h1>
		<h2>Binomial Coefficient Matrix </h2>
		{html}
		"""
		return html_table_with_styles
	return render_template('bin_stats.html')

if __name__ == '__main__':
	with app.app_context():
		db.create_all()
		PendingTransactionDatabase.genisis()
	app.run(debug=True,host="0.0.0.0",port=8080)
	while True:
		update()