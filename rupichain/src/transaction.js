'use strict';

/**
 * Transaction module using ECDSA secp256k1 (via `elliptic` npm package).
 *
 * For environments without npm dependencies installed, the test.js file
 * uses Node built-in crypto with P-256 (prime256v1) as a standalone test.
 */

const crypto = require('crypto');

// Try to load elliptic; if not installed, fall back to a stub that signals
// the caller to install dependencies.
let ec;
try {
  const { ec: EC } = require('elliptic');
  ec = new EC('secp256k1');
} catch (e) {
  ec = null;
}

function sha256(data) {
  return crypto.createHash('sha256').update(data).digest('hex');
}

function doubleSha256(data) {
  return sha256(sha256(data));
}

// ---------------------------------------------------------------------------
// Transaction
// ---------------------------------------------------------------------------
class Transaction {
  /**
   * @param {object} opts
   * @param {string} opts.sender      - sender address (hex public key hash)
   * @param {string} opts.recipient   - recipient address
   * @param {number} opts.amount      - amount in RUPI
   * @param {number} [opts.fee=0]     - miner fee
   * @param {string} [opts.signature] - DER-encoded hex signature
   * @param {number} [opts.timestamp]
   * @param {string} [opts.type]      - 'transfer' | 'coinbase'
   * @param {string} [opts.publicKey] - sender's full public key (hex) for verification
   */
  constructor({
    id        = null,
    sender,
    recipient,
    amount,
    fee       = 0,
    signature = null,
    timestamp = Date.now(),
    type      = 'transfer',
    publicKey = null,
  } = {}) {
    this.sender    = sender;
    this.recipient = recipient;
    this.amount    = amount;
    this.fee       = fee;
    this.signature = signature;
    this.timestamp = timestamp;
    this.type      = type;
    this.publicKey = publicKey;   // needed for verification
    this.id        = id || this._calculateId();
  }

  _calculateId() {
    return doubleSha256(this._getSignableData());
  }

  _getSignableData() {
    return JSON.stringify({
      sender:    this.sender,
      recipient: this.recipient,
      amount:    this.amount,
      fee:       this.fee,
      timestamp: this.timestamp,
      type:      this.type,
    });
  }

  /**
   * Sign the transaction using an elliptic secp256k1 key pair.
   * @param {object} keyPair - elliptic KeyPair object
   */
  sign(keyPair) {
    if (!ec) throw new Error('elliptic package not installed. Run: npm install');
    const hash = sha256(this._getSignableData());
    const sig  = keyPair.sign(hash, 'hex');
    this.signature = sig.toDER('hex');
    this.publicKey = keyPair.getPublic('hex');
    this.id        = this._calculateId();
    return this;
  }

  /**
   * Verify the transaction signature.
   */
  verify() {
    if (this.type === 'coinbase') return true;
    if (!ec) throw new Error('elliptic package not installed. Run: npm install');
    if (!this.signature || !this.publicKey) return false;

    try {
      const hash   = sha256(this._getSignableData());
      const pubKey = ec.keyFromPublic(this.publicKey, 'hex');
      return pubKey.verify(hash, this.signature);
    } catch (e) {
      return false;
    }
  }

  isValid() {
    if (this.type === 'coinbase') return true;
    if (!this.sender || !this.recipient)  return false;
    if (typeof this.amount !== 'number' || this.amount <= 0) return false;
    if (!this.signature) return false;
    return this.verify();
  }

  toJSON() {
    return {
      id:        this.id,
      sender:    this.sender,
      recipient: this.recipient,
      amount:    this.amount,
      fee:       this.fee,
      signature: this.signature,
      publicKey: this.publicKey,
      timestamp: this.timestamp,
      type:      this.type,
    };
  }
}

// ---------------------------------------------------------------------------
// Factory helpers
// ---------------------------------------------------------------------------

/**
 * Create a coinbase (mining reward) transaction.
 */
function createCoinbase(recipient, amount, blockIndex) {
  return new Transaction({
    sender:    'COINBASE',
    recipient,
    amount,
    fee:       0,
    type:      'coinbase',
    timestamp: Date.now(),
  });
}

/**
 * Create and sign a transfer transaction.
 * @param {string} senderAddress
 * @param {string} recipient
 * @param {number} amount
 * @param {number} fee
 * @param {object} keyPair - elliptic KeyPair
 */
function createTransfer(senderAddress, recipient, amount, fee, keyPair) {
  if (!ec) throw new Error('elliptic package not installed. Run: npm install');
  const tx = new Transaction({
    sender: senderAddress,
    recipient,
    amount,
    fee,
    type: 'transfer',
  });
  tx.sign(keyPair);
  return tx;
}

module.exports = { Transaction, createCoinbase, createTransfer, sha256, doubleSha256 };
