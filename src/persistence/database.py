from __future__ import annotations
import sqlite3

import blockchain


class P2PDatabaseIntegrityError(Exception):
    pass


class Database:
    DATABASE_FILE_NAME = "p2p.db"
    SQL_INIT_SCRIPT = "init.sql"

    def __init__(self, db_file_name: str | None = None, sql_init: str | None = None) -> None:
        self.database_file_name = Database.DATABASE_FILE_NAME if db_file_name is None else db_file_name
        self.sql_init_script = Database.SQL_INIT_SCRIPT if sql_init is None else sql_init
        self.db = sqlite3.connect(self.database_file_name, check_same_thread=False)
        self.db.execute('PRAGMA foreign_keys = ON') # to enable foreign key on cascade deletion
        self.cursor = self.db.cursor()
        self._init_db()

    def _init_db(self):
        with open(self.sql_init_script, 'r') as sql_file:
            sql_script = sql_file.read()
        self.cursor.executescript(sql_script)
        self.db.commit()

    def stop(self):
        self.db.close()

    def get_node_db_id(self, node_address: str) -> int | None:
        query = '''select id from node where node.full_address = "%s" ''' % node_address
        self.cursor.execute(query)
        res = self.cursor.fetchone()
        return None if res is None else res[0]

    def get_node_blockchain_state(self, node_address: str) -> blockchain.Blockchain | None:
        '''
        If there was found a blockchain state for specified node, than whole blockchain is recreated from db else None is returned
        '''
        node_db_id = self.get_node_db_id(node_address)
        if node_db_id is None:  # No node record in database
            return None
        else:
            return self.recreate_blockchain_from_db(node_db_id)

    def get_node_stored_transactions(self, node_address: str) -> list[blockchain.Transaction] | None:
        '''
        Return list of transactions for specified node (if any)
        '''
        node_db_id = self.get_node_db_id(node_address)
        if node_db_id is None:  # No node record in database
            return None
        else:
            transactions: list[blockchain.Transaction] = []
            query = '''SELECT sender, receiver, amount, transaction_timestamp FROM node_transaction where node_id = %d''' % node_db_id
            res = self.cursor.execute(query).fetchall()
            for queried_t in res:
                transactions.append(blockchain.Transaction(queried_t[0], queried_t[1], queried_t[2], queried_t[3]))
            return transactions

    def init_node_blockchain(self, node_address: str, blockchain: blockchain.Blockchain):
        '''
        Initialize new node in db with specified blockchain
        '''
        node_db_id = self.get_node_db_id(node_address)
        if node_db_id is None:
            insert_node_query = '''INSERT INTO NODE (full_address) VALUES ("%s")''' % node_address
            self.cursor.execute(insert_node_query)
            self.db.commit()
            self.node_new_blockchain(node_address, blockchain)
        else:
            raise P2PDatabaseIntegrityError("Trying to initialize node record with new blockchain for existing node %s" % node_address)

    def node_new_blockchain(self, node_address: str, blockchain: blockchain.Blockchain):
        '''
        Deletes previous blockchain assigned to node and assigns a new one
        '''
        node_db_id = self.get_node_db_id(node_address)
        if (node_db_id is None):
            raise P2PDatabaseIntegrityError("Adding new blockchain for non existing node %s" % node_address)
        delete_query = '''DELETE FROM blockchain WHERE node_id = "%d"''' % node_db_id
        new_blockchain_query = '''INSERT INTO blockchain (node_id) VALUES ("%d")''' % node_db_id
        self.cursor.execute(delete_query)
        self.cursor.execute(new_blockchain_query)
        self.db.commit()
        self.node_new_block(node_address, block_seq=blockchain.blocks)

    def node_new_block(self, node_address: str, block: blockchain.Block | None = None, block_seq: list[blockchain.Block] | None = None):
        node_db_id = self.get_node_db_id(node_address)
        if (node_db_id is None):
            raise P2PDatabaseIntegrityError("Adding new block for non existing node %s" % node_address)
        blockchain_db_id = self.cursor.execute('''select id from blockchain where node_id = "%d" ''' % node_db_id).fetchone()[0]

        if (block is not None):
            block_seq = [block]

        insert_block_query = '''INSERT INTO block (blockchain_id, block_index, block_timestamp, prev_hash, block_hash) VALUES (?,?,?,?,?)'''
        to_insert = [(blockchain_db_id, block.index, block.timestamp, block.prev_hash, block.block_hash)
                     for block in block_seq]  # type: ignore
        self.cursor.executemany(insert_block_query, to_insert)
        self.db.commit()
        for block in block_seq:  # type:ignore
            self.node_new_block_transaction(node_address, block, transaction_seq=block.data)

    def node_new_block_transaction(
            self, node_address: str, block: blockchain.Block, transaction: blockchain.Transaction | None = None,
            transaction_seq: list[blockchain.Transaction] | None = None):
        node_db_id = self.get_node_db_id(node_address)
        if (node_db_id is None):
            raise P2PDatabaseIntegrityError("Adding new block transaction for non existing node %s" % node_address)
        block_db_id = self.cursor.execute(
            '''select block.id from block inner join blockchain on block.blockchain_id=blockchain.id where blockchain.node_id = "%s" and block.block_index = %d''' %
            (node_db_id, block.index)).fetchone()[0]
        if (transaction is not None):
            transaction_seq = [transaction]

        insert_transaction_query = '''INSERT INTO block_transaction (block_id, sender, receiver, amount, transaction_timestamp) VALUES (?,?,?,?,?)'''
        to_insert = [(block_db_id, t.sender, t.receiver, t.amount, t.timestamp) for t in transaction_seq]  # type: ignore
        self.cursor.executemany(insert_transaction_query, to_insert)
        self.db.commit()

    def recreate_blockchain_from_db(self, node_db_id: int) -> blockchain.Blockchain:
        blocks: list[blockchain.Block] = []
        query_blocks = '''select block.id, block_index, block_timestamp, prev_hash, block_hash from block inner join blockchain on block.blockchain_id=blockchain.id where blockchain.node_id = "%s"''' % node_db_id
        for queried_b in self.cursor.execute(query_blocks).fetchall():
            if (queried_b[1] == 0):  # genesis block
                blocks.append(blockchain.Block.create_genesis())
                continue
            query_transactions = '''select sender, receiver, amount, transaction_timestamp from block_transaction where block_id = %d ''' % queried_b[
                0]
            queried_t = self.cursor.execute(query_transactions).fetchall()
            transactions: list[blockchain.Transaction] = [blockchain.Transaction(t[0], t[1], t[2], t[3]) for t in queried_t]
            blocks.append(blockchain.Block(queried_b[1], queried_b[2], transactions, queried_b[3], queried_b[4]))
        sorted_blocks_by_index = sorted(blocks, key=lambda b: b.index)
        return blockchain.Blockchain(sorted_blocks_by_index)

    def store_node_transaction(self, node_address: str, transaction: blockchain.Transaction):
        node_db_id = self.get_node_db_id(node_address)
        if (node_db_id is None):
            raise P2PDatabaseIntegrityError("Storing node transaction for non existing node %s" % node_address)

        insert_transaction_query = '''INSERT INTO node_transaction (node_id, sender, receiver, amount, transaction_timestamp) VALUES (%d,"%s","%s",%d,%d)''' % (
            node_db_id, transaction.sender, transaction.receiver, transaction.amount, transaction.timestamp)
        self.cursor.execute(insert_transaction_query)
        self.db.commit()

    def clear_node_transactions(self, node_address: str):
        node_db_id = self.get_node_db_id(node_address)
        if (node_db_id is None):
            raise P2PDatabaseIntegrityError("Clearing node transactions for non existing node %s" % node_address)
        delete_query = delete_query = '''DELETE FROM node_transaction WHERE node_id = "%d"''' % node_db_id
        self.cursor.execute(delete_query)
        self.db.commit()


if __name__ == '__main__':
    db = Database()
