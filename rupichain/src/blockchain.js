'use strict';

const crypto = require('crypto');

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const INITIAL_REWARD       = 50;          // RUPI
const HALVING_INTERVAL     = 210_000;     // blocks
const BLOCK_TIME_TARGET    = 10_000;      // ms  (10 seconds)
const DIFFICULTY_ADJUST_INTERVAL = 10;   // blocks
const MIN_DIFFICULTY       = 1;
const MAX_DIFFICULTY       = 32;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function sha256(data) {
  return crypto.createHash('sha256').update(data).digest('hex');
}

function doubleSha256(data) {
  return sha256(sha256(data));
}

// ---------------------------------------------------------------------------
// Transaction model (lightweight – full class is in transaction.js)
// ---------------------------------------------------------------------------
class Transaction {
  constructor({ id, sender, recipient, amount, fee = 0, signature = null, timestamp = Date.now(), type = 'transfer' } = {}) {
    this.id        = id || this._generateId();
    this.sender    = sender;
    this.recipient = recipient;
    this.amount    = amount;
    this.fee       = fee;
    this.signature = signature;
    this.timestamp = timestamp;
    this.type      = type;   // 'transfer' | 'coinbase'
  }

  _generateId() {
    return doubleSha256(`${Date.now()}${Math.random()}`);
  }

  getData() {
    return JSON.stringify({
      sender:    this.sender,
      recipient: this.recipient,
      amount:    this.amount,
      fee:       this.fee,
      timestamp: this.timestamp,
      type:      this.type,
    });
  }

  isValid() {
    if (this.type === 'coinbase') return true;
    if (!this.sender || !this.recipient) return false;
    if (this.amount <= 0) return false;
    // Full signature verification is done by the Transaction class in transaction.js
    // Here we just check structural integrity
    return true;
  }
}

// ---------------------------------------------------------------------------
// Block
// ---------------------------------------------------------------------------
class Block {
  constructor({
    index,
    timestamp,
    transactions = [],
    previousHash = '0'.repeat(64),
    nonce        = 0,
    difficulty   = 1,
    minerAddress = '',
    hash         = null,
  } = {}) {
    this.index        = index;
    this.timestamp    = timestamp || Date.now();
    this.transactions = transactions;
    this.previousHash = previousHash;
    this.nonce        = nonce;
    this.difficulty   = difficulty;
    this.minerAddress = minerAddress;
    this.hash         = hash || this.calculateHash();
  }

  calculateHash() {
    const header = JSON.stringify({
      index:        this.index,
      timestamp:    this.timestamp,
      txRoot:       this._merkleRoot(),
      previousHash: this.previousHash,
      nonce:        this.nonce,
      difficulty:   this.difficulty,
      minerAddress: this.minerAddress,
    });
    return doubleSha256(header);
  }

  _merkleRoot() {
    if (!this.transactions || this.transactions.length === 0) return '0'.repeat(64);
    let hashes = this.transactions.map(tx => sha256(tx.id || JSON.stringify(tx)));
    while (hashes.length > 1) {
      const next = [];
      for (let i = 0; i < hashes.length; i += 2) {
        const left  = hashes[i];
        const right = hashes[i + 1] || hashes[i];
        next.push(sha256(left + right));
      }
      hashes = next;
    }
    return hashes[0];
  }

  getTarget() {
    return '0'.repeat(this.difficulty);
  }

  meetsTarget(hash) {
    return hash.startsWith(this.getTarget());
  }

  isHashValid() {
    return this.hash === this.calculateHash() && this.meetsTarget(this.hash);
  }

  toJSON() {
    return {
      index:        this.index,
      timestamp:    this.timestamp,
      transactions: this.transactions,
      previousHash: this.previousHash,
      hash:         this.hash,
      nonce:        this.nonce,
      difficulty:   this.difficulty,
      minerAddress: this.minerAddress,
    };
  }
}

// ---------------------------------------------------------------------------
// Blockchain
// ---------------------------------------------------------------------------
class Blockchain {
  constructor() {
    this.chain    = [];
    this.mempool  = [];  // pending transactions
    this._createGenesisBlock();
  }

  // ---- Genesis ----
  _createGenesisBlock() {
    const genesis = new Block({
      index:        0,
      timestamp:    1700000000000,   // fixed timestamp for deterministic hash
      transactions: [],
      previousHash: '0'.repeat(64),
      nonce:        0,
      difficulty:   1,
      minerAddress: 'GENESIS',
    });
    // Force a clean hash (genesis doesn't need PoW)
    genesis.hash = genesis.calculateHash();
    this.chain.push(genesis);
  }

  // ---- Accessors ----
  getLatestBlock()  { return this.chain[this.chain.length - 1]; }
  getHeight()       { return this.chain.length - 1; }

  // ---- Difficulty ----
  getCurrentDifficulty() {
    const height = this.getHeight();
    if (height === 0) return MIN_DIFFICULTY;

    // Only adjust every DIFFICULTY_ADJUST_INTERVAL blocks
    const base = Math.floor(height / DIFFICULTY_ADJUST_INTERVAL) * DIFFICULTY_ADJUST_INTERVAL;
    if (base === 0) return MIN_DIFFICULTY;

    const blockAtBase  = this.chain[base];
    const blockBefore  = this.chain[Math.max(0, base - DIFFICULTY_ADJUST_INTERVAL)];

    const elapsed      = blockAtBase.timestamp - blockBefore.timestamp;
    const expected     = BLOCK_TIME_TARGET * DIFFICULTY_ADJUST_INTERVAL;
    const prevDiff     = blockAtBase.difficulty;

    let newDiff = Math.round(prevDiff * (expected / Math.max(elapsed, 1)));
    newDiff     = Math.max(MIN_DIFFICULTY, Math.min(MAX_DIFFICULTY, newDiff));
    return newDiff;
  }

  // ---- Mining reward (with halving) ----
  getMiningReward(blockIndex) {
    const halvings = Math.floor(blockIndex / HALVING_INTERVAL);
    if (halvings >= 64) return 0;    // max 64 halvings
    return INITIAL_REWARD / Math.pow(2, halvings);
  }

  getTotalSupply() {
    return this.chain.reduce((sum, block) => {
      const coinbase = block.transactions.find(tx => tx.type === 'coinbase');
      return sum + (coinbase ? coinbase.amount : 0);
    }, 0);
  }

  // ---- Mempool ----
  addToMempool(transaction) {
    // Basic validation
    if (!transaction.sender || !transaction.recipient || !transaction.amount) {
      throw new Error('Invalid transaction: missing fields');
    }
    if (transaction.amount <= 0) {
      throw new Error('Invalid transaction: amount must be positive');
    }
    // Check for duplicate
    const exists = this.mempool.some(tx => tx.id === transaction.id);
    if (exists) throw new Error('Transaction already in mempool');

    this.mempool.push(transaction);
    return true;
  }

  getPendingTransactions() {
    return [...this.mempool];
  }

  _clearMempool(confirmedTxIds) {
    this.mempool = this.mempool.filter(tx => !confirmedTxIds.includes(tx.id));
  }

  // ---- Create a candidate block (without PoW) ----
  createCandidateBlock(minerAddress) {
    const latest     = this.getLatestBlock();
    const index      = latest.index + 1;
    const difficulty = this.getCurrentDifficulty();
    const reward     = this.getMiningReward(index);

    const coinbase = new Transaction({
      type:      'coinbase',
      sender:    'COINBASE',
      recipient: minerAddress,
      amount:    reward,
      fee:       0,
      timestamp: Date.now(),
    });

    // Take up to 100 highest-fee transactions from mempool
    const sorted  = [...this.mempool].sort((a, b) => b.fee - a.fee);
    const txSlice = sorted.slice(0, 100);

    // Add total fees to coinbase
    const totalFees = txSlice.reduce((sum, tx) => sum + (tx.fee || 0), 0);
    coinbase.amount += totalFees;

    const block = new Block({
      index,
      timestamp:    Date.now(),
      transactions: [coinbase, ...txSlice],
      previousHash: latest.hash,
      nonce:        0,
      difficulty,
      minerAddress,
    });

    return block;
  }

  // ---- Add a mined block ----
  addBlock(block) {
    if (!this.isValidNewBlock(block, this.getLatestBlock())) {
      throw new Error(`Invalid block at index ${block.index}`);
    }
    // Reconstruct as Block instance if plain object
    const b = block instanceof Block ? block : new Block(block);
    this.chain.push(b);

    // Remove confirmed txs from mempool
    const txIds = b.transactions.map(tx => tx.id);
    this._clearMempool(txIds);
    return b;
  }

  // ---- Validation ----
  isValidNewBlock(newBlock, previousBlock) {
    const b  = newBlock instanceof Block ? newBlock : new Block(newBlock);
    const pb = previousBlock instanceof Block ? previousBlock : new Block(previousBlock);

    if (b.index !== pb.index + 1)           return false;
    if (b.previousHash !== pb.hash)          return false;
    if (b.calculateHash() !== b.hash)        return false;
    if (!b.meetsTarget(b.hash))              return false;
    return true;
  }

  isChainValid(chain = this.chain) {
    // Genesis check
    const genesis = chain[0];
    if (!genesis) return false;

    for (let i = 1; i < chain.length; i++) {
      const block = chain[i] instanceof Block ? chain[i] : new Block(chain[i]);
      const prev  = chain[i - 1] instanceof Block ? chain[i - 1] : new Block(chain[i - 1]);
      if (!this.isValidNewBlock(block, prev)) return false;
    }
    return true;
  }

  // ---- Replace chain (longest chain rule) ----
  replaceChain(newChain) {
    if (newChain.length <= this.chain.length) return false;
    if (!this.isChainValid(newChain)) return false;
    this.chain = newChain.map(b => b instanceof Block ? b : new Block(b));
    return true;
  }

  // ---- Balance ----
  getBalance(address) {
    let balance = 0;
    for (const block of this.chain) {
      for (const tx of block.transactions) {
        if (tx.recipient === address) balance += tx.amount;
        if (tx.sender    === address) balance -= (tx.amount + (tx.fee || 0));
      }
    }
    // Also check mempool for pending outgoing
    for (const tx of this.mempool) {
      if (tx.sender === address) balance -= (tx.amount + (tx.fee || 0));
    }
    return Math.max(0, balance);
  }

  // ---- Serialization ----
  toJSON() {
    return this.chain.map(b => b.toJSON ? b.toJSON() : b);
  }
}

module.exports = { Blockchain, Block, Transaction, sha256, doubleSha256 };
