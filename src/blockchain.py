from datetime import datetime
from hashlib import sha256


class Transaction:
    def __init__(self, sender: str, receiver: str, amount: int, timestamp: datetime) -> None:
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.timestamp = timestamp
        pass

    def to_bytes(self) -> bytes:
        b_transaction = []
        b_transaction.append(bytes(self.sender, encoding='utf-8'))
        b_transaction.append(bytes(self.receiver, encoding='utf-8'))
        b_transaction.append(self.amount.to_bytes(length=32, byteorder='big'))
        b_transaction.append(bytes(str(self.timestamp), encoding='utf-8'))
        return b''.join(b_transaction)


class Block:
    def __init__(self, index: int, timestamp: datetime | None, data: list[Transaction] | None, prev_hash: str | None) -> None:
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.prev_hash = prev_hash
        self.block_hash = self.generate_block_hash()

    @classmethod
    def create_genesis(cls):
        return cls(0, None, None, None)

    @classmethod
    def create_block(cls, index: int, timestamp: datetime, data: list[Transaction], prev_hash: str):
        return cls(index, timestamp, data, prev_hash)

    def generate_block_hash(self) -> str:
        to_hash = []
        b_index = self.index.to_bytes(length=32, byteorder='big')
        to_hash.append(b_index)
        if self.timestamp is not None:
            b_timestamp = bytes(str(self.timestamp), encoding='utf-8')
            to_hash.append(b_timestamp)
        if (self.data is not None):
            b_data = b''.join([t.to_bytes() for t in self.data])
            to_hash.append(b_data)
        if (self.prev_hash is not None):
            b_prev_hash = bytes(self.prev_hash, encoding='utf-8')
            to_hash.append(b_prev_hash)
        return sha256(b''.join(to_hash)).hexdigest()


class Blockchain:
    def __init__(self) -> None:
        pass
