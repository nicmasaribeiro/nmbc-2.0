#!/usr/bin/env python3

from transaction import Transaction
import hashlib
import json
from time import time
from typing import List


class Block:
	def __init__(self, index: int, timestamp: float, transactions: List[Transaction], previous_hash: str, proof: int):
		self.index = index
		self.timestamp = timestamp
		self.transactions = transactions
		self.previous_hash = previous_hash
		self.proof = proof
		self.hash = self.hash_block()
		
	def hash_block(self) -> str:
		block_string = json.dumps(self.__dict__, sort_keys=True, default=str).encode()
		return hashlib.sha256(block_string).hexdigest()
	
	def __repr__(self):
		return f"Block(Index: {self.index}, Hash: {self.hash})"
	
import hashlib
import json
import requests
from time import time
from urllib.parse import urlparse
from typing import List, Set

class Blockchain:
	def __init__(self):
		self.chain: List[Block] = []
		self.current_transactions: List[Transaction] = []
		self.nodes: Set[str] = set()
		self.create_genesis_block()
		
	def create_genesis_block(self):
		genesis_block = Block(index=0, timestamp=time(), transactions=[], previous_hash='0', proof=1)
		self.chain.append(genesis_block)
		
	def register_node(self, address: str):
		parsed_url = urlparse(address)
		self.nodes.add(parsed_url.netloc)
		
	def new_transaction(self, transaction: Transaction):
		if transaction.is_valid():
			self.current_transactions.append(transaction)
			return True
		return False
	
	def get_last_block(self) -> Block:
		return self.chain[-1]
	
	def add_block(self, proof: int):
		last_block = self.get_last_block()
		new_block = Block(index=last_block.index + 1, timestamp=time(), transactions=self.current_transactions, previous_hash=last_block.hash, proof=proof)
		self.current_transactions = []
		self.chain.append(new_block)
		
	def proof_of_work(self, last_proof: int) -> int:
		proof = 0
		while not self.is_valid_proof(last_proof, proof):
			proof += 1
		return proof
	
	def is_valid_proof(self, last_proof: int, proof: int) -> bool:
		guess = f'{last_proof}{proof}'.encode()
		guess_hash = hashlib.sha256(guess).hexdigest()
		return guess_hash[:4] == "0000"
	
	def is_chain_valid(self, chain: List[Block]) -> bool:
		for i in range(1, len(chain)):
			current_block = chain[i]
			previous_block = chain[i - 1]
			if current_block.previous_hash != previous_block.hash:
				return False
			if not self.is_valid_proof(previous_block.proof, current_block.proof):
				return False
		return True
	
	def resolve_conflicts(self) -> bool:
		neighbours = self.nodes
		new_chain = None
		
		max_length = len(self.chain)
		
		for node in neighbours:
			response = requests.get(f'http://{node}/chain')
			
			if response.status_code == 200:
				length = response.json()['length']
				chain = response.json()['chain']
				
				if length > max_length and self.is_chain_valid(chain):
					max_length = length
					new_chain = chain
					
		if new_chain:
			self.chain = [Block(**block) for block in new_chain]
			return True
		
		return False
	
	def broadcast_transaction(self, transaction: Transaction):
		for node in self.nodes:
			response = requests.post(f'http://{node}/transactions/new', json=transaction.to_dict())
			if response.status_code != 201:
				return False
		return True
	
	def broadcast_block(self, block: Block):
		for node in self.nodes:
			response = requests.post(f'http://{node}/block/new', json=block.__dict__)
			if response.status_code != 201:
				return False
		return True
	