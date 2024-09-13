import numpy as np
import datetime as dt
from models import *
from hashlib import sha512,sha256
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.hashes import SHA512

class BCPrivateBlock:
	def __init__(self, index, previous_hash, timestamp, transactions, hash=None):
		self.index = index
		self.previous_hash = previous_hash
		self.timestamp = timestamp
		self.transactions = transactions
		self.hash = hash or self.calculate_hash()
		
	def calculate_hash(self):
		return sha512(str(self.index).encode())

class Coin:
	def __init__(self):
		self.market_cap = 0.0001
		self.staked_coins = []
		self.new_coins = 0
		self.dollar_value = 100
		self.exchange = 0 
		
	def process_coins(self):
		self.new_coins += 1
		return self.new_coins
	
	def set_dollar_value(self, value):
		self.dollar_value = value
		
	def get_dollar_value(self):
		return self.dollar_value
	
	def stake_coins(self, approved_transactions, pending_transactions):
		v = self.process_coins()
		len1 = len(pending_transactions)
		len2 = len(approved_transactions)
		pending_sum = sum(pending_transactions)
		approved_sum = sum(approved_transactions)
		total_sum = pending_sum + approved_sum
		u = (len1 + len2) / total_sum * v
		return u
	
class BCNetwork:
	def __init__(self):
		self.pending_transactions = []
		self.approved_transactions = []
		self.stake = []
		self.web = defaultdict(float)
		self.senders = []
		self.money = []
		self.receipts = []
		self.market_cap = 0.0001
		
	def set_market_cap(self, value):
		self.market_cap = value
	
	def add_transaction(self,transaction):
		self.pending_transactions.append(transaction)
		
	def generate_key(self, key_size=2048):
		private_key = rsa.generate_private_key(
			public_exponent=65537,
			key_size=key_size,
			backend=default_backend()
		)
		public_key = private_key.public_key()
		return private_key, public_key
	
	def sign_packet(self, packet: bytes, private_key):
		hash = int.from_bytes(sha512(packet).digest(), byteorder='big')
		signature = pow(hash, private_key.private_numbers().d, private_key.private_numbers().public_numbers.n)
		return signature

	def verify_packet(self, packet: bytes, key, signature):
		hash = int.from_bytes(sha512(packet).digest(), byteorder='big')
		hashFromSignature = pow(signature, key.public_numbers().e, key.public_numbers().n)
		print("Signature valid:", hash == hashFromSignature)
		return hash == hashFromSignature

	
	def get_stake(self):
		return self.stake
			
	def get_pending(self):
		return self.pending_transactions
			
	def get_approved(self):
		return self.approved_transactions
			
	def set_transaction(self, sender_wallet_address, recv_wallet_address, value):
		sender_wallet = Wallet.query.filter_by(address=sender_wallet_address).first()
		recv_wallet = Wallet.query.filter_by(address=recv_wallet_address).first()
		packet = str({'from':sender_wallet_address,'to':recv_wallet_address,'value':value}).encode()
		self.add_transaction(packet.hex())
		pending = PendingTransactionDatabase(txid=os.urandom(10).hex(),
									   username=sender_wallet.address,
									   from_address=sender_wallet.address,
									   to_address=recv_wallet.address,
									   amount=value,timestamp=dt.datetime.now(),
									   type='internal_wallet',
									   signature=str(sender_wallet.address).encode().hex())
		db.session.add(pending)
		db.session.commit()

	def set_investment(self, investor_wallet_address, value):
		investor_wallet = Wallet.query.filter_by(address=investor_wallet_address).first()
		user = Users.query.filter_by(username=investor_wallet_address).first()
		packet = str({'from':investor_wallet_address,'to':"market",'value':value}).encode()
		self.add_transaction(packet.hex())
		pending = PendingTransactionDatabase(txid=os.urandom(10).hex(),
									   username=investor_wallet.address,
									   from_address=user.personal_token,
									   to_address="market",
									   amount=value,
									   timestamp=dt.datetime.now(),
									   type='investment',
									   signature=str(investor_wallet.address).encode().hex())
		db.session.add(pending)
		db.session.commit()
		
	def process_transaction(self, sender_wallet_address, recv_wallet_address, txid ,value, coin, blockchain):
		pending = PendingTransactionDatabase().query.filter_by(txid=txid).first()
		sender_wallet = Wallet.query.filter_by(address=sender_wallet_address).first()
		recv_wallet = Wallet.query.filter_by(address=recv_wallet_address).first()
		sender_wallet.balance-=value
		recv_wallet.balance+=value
		db.session.commit()
		approved = TransactionDatabase(txid=pending.txid,
									   username=sender_wallet.address,
									   from_address=sender_wallet.address,
									   to_address=recv_wallet.address,
									   amount=value,timestamp=dt.datetime.now(),
									   type='internal_wallet',
									   signature=pending.signature)
		
		db.session.add(approved)
		db.session.commit()
		active_chain = TransactionDatabase.query.all()
		aChain = [ac.amount for ac in active_chain]
		pending_chain = PendingTransactionDatabase.query.all()
		pChain = [pc.amount for pc in pending_chain]
		result = coin.stake_coins(aChain,pChain)
		blockchain.stake.append(result)
		db.session.delete(pending)
		db.session.commit()
		return result

def process_investment(self, investor_wallet_address, txid ,value, coin, blockchain):
		user = Users.query.filter_by(username=investor_wallet_address).first()
		pending = PendingTransactionDatabase().query.filter_by(txid=txid).first()
		investor_wallet = Wallet.query.filter_by(address=investor_wallet_address).first()
		investor_wallet.balance-=value
		db.session.commit()
		approved = TransactionDatabase(txid=pending.txid,
									   username=investor_wallet.address,
									   from_address=user.personal_token,
									   to_address="market",
									   amount=value,timestamp=dt.datetime.now(),
									   type='investment',
									   signature=pending.signature)
		
		db.session.add(approved)
		db.session.commit()
		active_chain = TransactionDatabase.query.all()
		aChain = [ac.amount for ac in active_chain]
		pending_chain = PendingTransactionDatabase.query.all()
		pChain = [pc.amount for pc in pending_chain]
		result = coin.stake_coins(aChain,pChain)
		blockchain.stake.append(result)
		db.session.delete(pending)
		db.session.commit()
		return result

class BCBlockchain(Network):
	def __init__(self):
		super(Network).__init__()
		self.chain = [self.create_genesis_block()]
		self.transactions_pending_verification = []
		self.pending_transactions = []
		self.stake = []
		self.difficulty = 4
		self.mining_reward = 1

	def get_pending(self):
		return self.pending_transactions
	
	def get_approved(self):
		return self.chain
	
	def create_genesis_block(self):
		return PrivateBlock(0, "0", dt.date.today(), [], "0")
	
	def get_latest_block(self):
		return self.chain[-1]
	
	def get_latest_block_hash(self):
		return hash(str(self.chain[-1]))
	
	def mine_pending_transactions(self, mining_reward_address):
		reward_tx = TransactionDatabase(None, mining_reward_address, self.mining_reward)
		self.pending_transactions.append(reward_tx)
		block = PrivateBlock(len(self.chain)+1, self.get_latest_block_hash(), int(dt.datetime.now()), self.pending_transactions)
		block.hash = block.calculate_hash()  # Simple hash assignment
		self.chain.append(block)
		self.pending_transactions.clear()
	
	def proof_of_work(self,block_data, difficulty=7):
		nonce = 0
		start_time = time.time()
		prefix = '0' * difficulty
		while True:
			nonce += 1
			text = str(block_data) + str(nonce)
			hash_result = sha256(text.encode()).hexdigest()
			if hash_result.startswith(prefix):
				end_time = time.time()
				time_taken = end_time - start_time
				return nonce, hash_result, time_taken
			
	def add_transaction(self, transaction):
		self.pending_transactions.append(transaction)
		
	def add_block(self,block):
		self.chain.append(block)
		
	def get_balance_of_address(self, address):
		balance = 0
		
		for block in self.chain:
			for trans in block.transactions:
				if trans.from_address == address:
					balance -= trans.amount
					
				if trans.to_address == address:
					balance += trans.amount
					
		return balance
	
	def is_chain_valid(self):
		for i in range(1, len(self.chain)):
			current_block = self.chain[i]
			previous_block = self.chain[i - 1]
			
			if current_block.hash != current_block.calculate_hash():
				return False
			
			if current_block.previous_hash != previous_block.hash:
				return False
			
			for transaction in current_block.transactions:
				if not transaction.is_valid():
					return False
				
		return True

