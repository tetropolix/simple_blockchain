from __future__ import annotations
from datetime import datetime
from hashlib import sha256
import logging

import protos.NodeRPCService_pb2 as NodeRPCService_pb2


class Transaction:
    def __init__(self, sender: str, receiver: str, amount: int, timestamp: int) -> None:
        self.sender = sender  # id of generating node
        self.receiver = receiver
        self.amount = amount
        self.timestamp = timestamp
        pass

    def __repr__(self):
        return "From {%s} .. To {%s} .. Amount {%d} .. Timestamp {%s}" % (
            self.sender, self.receiver, self.amount, datetime.utcfromtimestamp(self.timestamp).strftime("%d/%m/%Y, %H:%M:%S"))

    def to_bytes(self) -> bytes:
        b_transaction = []
        b_transaction.append(bytes(self.sender, encoding='utf-8'))
        b_transaction.append(bytes(self.receiver, encoding='utf-8'))
        b_transaction.append(self.amount.to_bytes(length=32, byteorder='big'))
        b_transaction.append(self.timestamp.to_bytes(length=32, byteorder='big'))
        return b''.join(b_transaction)

    def to_grpc_request(self) -> NodeRPCService_pb2.Transaction:
        return NodeRPCService_pb2.Transaction(
            sender=self.sender, receiver=self.receiver, amount=self.amount, timestamp=self.timestamp)


class Block:
    def __init__(
            self, index: int, timestamp: int | None, data: list[Transaction] | None, prev_hash: str | None, block_hash: str | None) -> None:
        if (data is not None and (len(data) != Blockchain.TRANSACTIONS_THRESHOLD)):
            raise ValueError('Trying to initialize block with %d transactions' % len(data))
        self.index = index
        self.timestamp = timestamp
        self.data = [] if not data else data
        self.prev_hash = prev_hash
        self.block_hash = self.generate_block_hash() if block_hash is None else block_hash

    def to_grpc_request(self) -> NodeRPCService_pb2.Block:
        return NodeRPCService_pb2.Block(
            index=self.index, timestamp=self.timestamp, prev_hash=self.prev_hash, block_hash=self.block_hash,
            data=[t.to_grpc_request() for t in self.data])

    @classmethod
    def create_genesis(cls):
        return cls(0, None, None, None, None)

    @classmethod
    def create_block(cls, index: int, timestamp: int, data: list[Transaction], prev_hash: str):
        return cls(index, timestamp, data, prev_hash, None)

    def generate_block_hash(self) -> str:
        to_hash = []
        b_index = self.index.to_bytes(length=32, byteorder='big')
        to_hash.append(b_index)
        if self.timestamp is not None:
            b_timestamp = self.timestamp.to_bytes(length=32, byteorder='big')
            to_hash.append(b_timestamp)
        if (self.data is not None):
            b_data = b''.join([t.to_bytes() for t in self.data])
            to_hash.append(b_data)
        if (self.prev_hash is not None):
            b_prev_hash = bytes(self.prev_hash, encoding='utf-8')
            to_hash.append(b_prev_hash)
        return sha256(b''.join(to_hash)).hexdigest()


class Blockchain:
    TRANSACTIONS_THRESHOLD = 1

    def __init__(self, blocks: list[Block] | None) -> None:
        if blocks is None:
            self.blocks: list[Block] = []
            self.blocks.append(Block.create_genesis())
            self.blocks = self.blocks*4
        else:
            self.blocks = blocks

    def __repr__(self):
        output = []
        fancy_blocks = min(10, len(self.blocks))
        fancy_blockchain = "chain: "
        for _ in range(0, fancy_blocks-1):
            fancy_blockchain += "[:]-->"
        fancy_blockchain += "[:]"
        output.append(fancy_blockchain)
        output.append('Num of block: %d' % len(self.blocks))
        output.append('Last block index: %d' % self.blocks[-1].index)
        output.append('Last block timestamp: %s' %
                      str(self.blocks[-1].timestamp))
        return "\n".join(output)

    @classmethod
    def logger(cls):
        return logging.getLogger(cls.__name__)

    def add_new_block(self, block: Block) -> bool:
        is_valid = self.verify_new_block(block)
        if (not is_valid):
            return False
        self.blocks.append(block)
        return True

    def verify_new_block(self, block: Block) -> bool:
        valid = True
        if (block.block_hash != block.generate_block_hash()):
            print('Block with index %s has invalid hash value' % block.index)
            valid = False
        if (block.prev_hash != self.blocks[-1].block_hash):
            print('Block with index %s has invalid value of prev block hash' % block.index)
            valid = False
        return valid

    def last_block(self) -> Block:
        return self.blocks[-1]
