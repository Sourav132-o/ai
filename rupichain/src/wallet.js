'use strict';

/**
 * Wallet module – uses elliptic secp256k1 for key generation and signing.
 * Addresses are RIPEMD-160(SHA-256(publicKey)) encoded as hex, prefixed with "RC".
 */

const crypto = require('crypto');

let ec;
try {
  const { ec: EC } = require('elliptic');
  ec = new EC('secp256k1');
} catch (e) {
  ec = null;
}

function sha256(data) {
  return crypto.createHash('sha256').update(data, 'hex').digest('hex');
}

function ripemd160(data) {
  return crypto.createHash('ripemd160').update(data, 'hex').digest('hex');
}

/**
 * Derive a Rupi Chain address from a public key hex string.
 * Format: "RC" + first 20 bytes (40 hex chars) of RIPEMD160(SHA256(pubKey))
 */
function publicKeyToAddress(publicKeyHex) {
  const step1 = sha256(publicKeyHex);
  const step2 = ripemd160(step1);
  return 'RC' + step2.slice(0, 40).toUpperCase();
}

// ---------------------------------------------------------------------------
// Wallet
// ---------------------------------------------------------------------------
class Wallet {
  constructor(privateKeyHex = null) {
    if (!ec) throw new Error('elliptic package not installed. Run: npm install');

    if (privateKeyHex) {
      this.keyPair = ec.keyFromPrivate(privateKeyHex, 'hex');
    } else {
      this.keyPair = ec.genKeyPair();
    }

    this.privateKey = this.keyPair.getPrivate('hex');
    this.publicKey  = this.keyPair.getPublic('hex');
    this.address    = publicKeyToAddress(this.publicKey);
  }

  /**
   * Sign a transaction object (must have _getSignableData method, i.e., Transaction instance).
   */
  signTransaction(transaction) {
    if (transaction.sender !== this.address) {
      throw new Error('Cannot sign transaction for another wallet address');
    }
    transaction.sign(this.keyPair);
    return transaction;
  }

  /**
   * Get balance for this wallet from a Blockchain instance.
   */
  getBalance(blockchain) {
    return blockchain.getBalance(this.address);
  }

  toJSON() {
    return {
      address:    this.address,
      publicKey:  this.publicKey,
      privateKey: this.privateKey,  // WARNING: never expose in production!
    };
  }

  /**
   * Export only the public info (safe to share).
   */
  toPublicJSON() {
    return {
      address:   this.address,
      publicKey: this.publicKey,
    };
  }
}

// ---------------------------------------------------------------------------
// Static helpers
// ---------------------------------------------------------------------------

/**
 * Generate a new wallet with a fresh key pair.
 */
function generateWallet() {
  return new Wallet();
}

/**
 * Restore a wallet from a private key hex string.
 */
function walletFromPrivateKey(privateKeyHex) {
  return new Wallet(privateKeyHex);
}

module.exports = { Wallet, generateWallet, walletFromPrivateKey, publicKeyToAddress };
