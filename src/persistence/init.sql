CREATE TABLE IF NOT EXISTS node(
    id INTEGER PRIMARY KEY,
    full_address VARCHAR(64) NOT NULL
);
CREATE TABLE IF NOT EXISTS blockchain(
    id INTEGER PRIMARY KEY,
    node_id INTEGER NOT NULL,
    FOREIGN KEY (node_id) REFERENCES node (id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS block(
    id INTEGER PRIMARY KEY,
    block_index INTEGER NOT NULL,
    block_timestamp INTEGER,
    prev_hash VARCHAR(256),
    block_hash VARCHAR(256),
    blockchain_id INTEGER NOT NULL,
    FOREIGN KEY (blockchain_id) REFERENCES blockchain (id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS block_transaction(
    id INTEGER PRIMARY KEY,
    sender VARCHAR(64) NOT NULL,
    receiver VARCHAR(64) NOT NULL,
    amount INTEGER NOT NULL,
    transaction_timestamp INTEGER NOT NULL,
    
    block_id INTEGER NOT NULL,
    FOREIGN KEY (block_id) REFERENCES block (id) ON DELETE CASCADE
);
-- Node's list of transactions for next block
CREATE TABLE IF NOT EXISTS node_transaction(
    id INTEGER PRIMARY KEY,
    sender VARCHAR(64) NOT NULL,
    receiver VARCHAR(64) NOT NULL,
    amount INTEGER NOT NULL,
    transaction_timestamp INTEGER NOT NULL,
    
    node_id INTEGER NOT NULL,
    FOREIGN KEY (node_id) REFERENCES node (id) ON DELETE CASCADE
);