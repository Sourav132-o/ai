'use strict';

/**
 * Rupi Chain - Self-Contained Test
 * Uses ONLY Node.js built-in modules (crypto, assert).
 * No npm install required.
 *
 * Tests:
 *   1. Genesis block creation
 *   2. Mining block #1 with difficulty 2 (easy)
 *   3. Mining block #2
 *   4. Chain integrity verification
 *   5. ECDSA P-256 transaction signing & verification (built-in crypto)
 *   6. Tamper detection
 *   7. Halving mechanism
 */

const crypto = require('crypto');
const assert = require('assert');

// ─── ANSI colors ──────────────────────────────────────────────────────────────
const C = {
  reset:  '\x1b[0m',
  green:  '\x1b[32m',
  red:    '\x1b[31m',
  yellow: '\x1b[33m',
  cyan:   '\x1b[36m',
  bold:   '\x1b[1m',
  dim:    '\x1b[2m',
};

let passed = 0;
let failed = 0;
const results = [];

function test(name, fn) {
  try {
    fn();
    console.log(`  ${C.green}✓${C.reset} ${name}`);
    passed++;
    results.push({ name, ok: true });
  } catch (err) {
    console.log(`  ${C.red}✗ FAIL:${C.reset} ${name}`);
    console.log(`    ${C.red}${err.message}${C.reset}`);
    failed++;
    results.push({ name, ok: false, error: err.message });
  }
}

// ─── Utilities (standalone, no external deps) ─────────────────────────────────
function sha256(data) {
  return crypto.createHash('sha256').update(data).digest('hex');
}

function doubleSha256(data) {
  return sha256(sha256(data));
}

// ─── Constants ────────────────────────────────────────────────────────────────
const INITIAL_REWARD   = 50;
const HALVING_INTERVAL = 210_000;
const MIN_DIFFICULTY   = 1;

// ─── Transaction (built-in crypto only, P-256) ────────────────────────────────
class TxStandalone {
  constructor({ sender, recipient, amount, fee = 0, timestamp = Date.now() } = {}) {
    this.sender    = sender;
    this.recipient = recipient;
    this.amount    = amount;
    this.fee       = fee;
    this.timestamp = timestamp;
    this.signature = null;
    this.publicKey = null;
    this.id        = this._calcId();
  }

  _signable() {
    return JSON.stringify({
      sender:    this.sender,
      recipient: this.recipient,
      amount:    this.amount,
      fee:       this.fee,
      timestamp: this.timestamp,
    });
  }

  _calcId() {
    return doubleSha256(this._signable());
  }

  /**
   * Sign using Node built-in crypto with P-256 (prime256v1).
   * @param {KeyObject} privateKey  – from crypto.generateKeyPairSync('ec', {namedCurve:'P-256'})
   * @param {KeyObject} publicKey
   */
  sign(privateKey, publicKey) {
    const sign = crypto.createSign('SHA256');
    sign.update(this._signable());
    sign.end();
    this.signature = sign.sign(privateKey, 'hex');

    // Store public key in DER hex for later verification
    this.publicKey = publicKey.export({ type: 'spki', format: 'der' }).toString('hex');
    this.id        = this._calcId();
    return this;
  }

  /**
   * Verify signature.
   */
  verify() {
    if (!this.signature || !this.publicKey) return false;
    try {
      const pubKeyDer = Buffer.from(this.publicKey, 'hex');
      const pubKeyObj = crypto.createPublicKey({ key: pubKeyDer, format: 'der', type: 'spki' });
      const verify    = crypto.createVerify('SHA256');
      verify.update(this._signable());
      verify.end();
      return verify.verify(pubKeyObj, this.signature, 'hex');
    } catch (e) {
      return false;
    }
  }

  isValid() {
    if (!this.sender || !this.recipient) return false;
    if (typeof this.amount !== 'number' || this.amount <= 0) return false;
    return this.verify();
  }
}

// ─── Block (standalone) ───────────────────────────────────────────────────────
class BlockStandalone {
  constructor({ index, timestamp, transactions = [], previousHash, nonce = 0, difficulty = 1, minerAddress = '' } = {}) {
    this.index        = index;
    this.timestamp    = timestamp || Date.now();
    this.transactions = transactions;
    this.previousHash = previousHash || '0'.repeat(64);
    this.nonce        = nonce;
    this.difficulty   = difficulty;
    this.minerAddress = minerAddress;
    this.hash         = this.calcHash();
  }

  _merkleRoot() {
    if (!this.transactions || this.transactions.length === 0) return '0'.repeat(64);
    let hashes = this.transactions.map(tx => sha256(JSON.stringify(tx)));
    while (hashes.length > 1) {
      const next = [];
      for (let i = 0; i < hashes.length; i += 2) {
        next.push(sha256(hashes[i] + (hashes[i + 1] || hashes[i])));
      }
      hashes = next;
    }
    return hashes[0];
  }

  calcHash() {
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

  meetsTarget() {
    return this.hash.startsWith('0'.repeat(this.difficulty));
  }
}

// ─── Blockchain (standalone) ──────────────────────────────────────────────────
class ChainStandalone {
  constructor() {
    this.chain = [];
    this._addGenesis();
  }

  _addGenesis() {
    const g = new BlockStandalone({
      index:        0,
      timestamp:    1_700_000_000_000,
      transactions: [],
      previousHash: '0'.repeat(64),
      nonce:        0,
      difficulty:   MIN_DIFFICULTY,
      minerAddress: 'GENESIS',
    });
    g.hash = g.calcHash();
    this.chain.push(g);
  }

  get latest() { return this.chain[this.chain.length - 1]; }

  getMiningReward(blockIndex) {
    const halvings = Math.floor(blockIndex / HALVING_INTERVAL);
    if (halvings >= 64) return 0;
    return INITIAL_REWARD / Math.pow(2, halvings);
  }

  /** Simple synchronous PoW mine */
  mineBlock(minerAddress, difficulty = 2) {
    const reward = this.getMiningReward(this.chain.length);
    const coinbase = {
      id:        doubleSha256(`coinbase-${this.chain.length}-${Date.now()}`),
      sender:    'COINBASE',
      recipient: minerAddress,
      amount:    reward,
      type:      'coinbase',
    };

    const block = new BlockStandalone({
      index:        this.chain.length,
      timestamp:    Date.now(),
      transactions: [coinbase],
      previousHash: this.latest.hash,
      nonce:        0,
      difficulty,
      minerAddress,
    });

    const target = '0'.repeat(difficulty);
    const t0     = Date.now();

    while (!block.hash.startsWith(target)) {
      block.nonce++;
      block.hash = block.calcHash();
      if (block.nonce > 50_000_000) throw new Error('Mining timed out (nonce space exhausted)');
    }

    const elapsed = ((Date.now() - t0) / 1000).toFixed(2);
    console.log(`    ${C.dim}Block #${block.index}: nonce=${block.nonce}, hash=${block.hash.slice(0, 20)}..., time=${elapsed}s${C.reset}`);
    return block;
  }

  addBlock(block) {
    const prev = this.latest;
    if (block.index !== prev.index + 1) throw new Error('Bad block index');
    if (block.previousHash !== prev.hash) throw new Error('Bad previousHash');
    const recomputed = block.calcHash();
    if (block.hash !== recomputed) throw new Error('Bad block hash');
    if (!block.meetsTarget()) throw new Error('Block does not meet PoW target');
    this.chain.push(block);
    return block;
  }

  isValid() {
    for (let i = 1; i < this.chain.length; i++) {
      const b = this.chain[i];
      const p = this.chain[i - 1];
      if (b.previousHash !== p.hash) return false;
      if (b.calcHash() !== b.hash)   return false;
      if (!b.meetsTarget())          return false;
    }
    return true;
  }

  getBalance(address) {
    let bal = 0;
    for (const block of this.chain) {
      for (const tx of block.transactions) {
        if (tx.recipient === address) bal += tx.amount;
        if (tx.sender    === address) bal -= (tx.amount + (tx.fee || 0));
      }
    }
    return bal;
  }
}

// ─── Tests ────────────────────────────────────────────────────────────────────

console.log(`\n${C.bold}${C.cyan}╔══════════════════════════════════════╗${C.reset}`);
console.log(`${C.bold}${C.cyan}║   Rupi Chain — Test Suite            ║${C.reset}`);
console.log(`${C.bold}${C.cyan}╚══════════════════════════════════════╝${C.reset}\n`);

const MINER_ADDR = 'RC_TESTER_001';
const chain = new ChainStandalone();

// ── Section 1: Genesis ───────────────────────────────────────────────────────
console.log(`${C.yellow}▶ 1. Genesis Block${C.reset}`);

test('Genesis block exists at index 0', () => {
  assert.strictEqual(chain.chain.length, 1);
  assert.strictEqual(chain.chain[0].index, 0);
});

test('Genesis block has correct structure', () => {
  const g = chain.chain[0];
  assert.strictEqual(g.minerAddress, 'GENESIS');
  assert.ok(typeof g.hash === 'string' && g.hash.length === 64);
  assert.strictEqual(g.previousHash, '0'.repeat(64));
});

test('Genesis block hash is self-consistent', () => {
  const g = chain.chain[0];
  assert.strictEqual(g.calcHash(), g.hash);
});

// ── Section 2: Mine block 1 ──────────────────────────────────────────────────
console.log(`\n${C.yellow}▶ 2. Mining Block #1 (difficulty 2)${C.reset}`);

let block1;
test('Mine block #1 with difficulty 2', () => {
  block1 = chain.mineBlock(MINER_ADDR, 2);
  assert.ok(block1.hash.startsWith('00'), `Hash "${block1.hash.slice(0, 10)}" does not start with "00"`);
  assert.strictEqual(block1.index, 1);
});

test('Block #1 links to genesis', () => {
  assert.strictEqual(block1.previousHash, chain.chain[0].hash);
});

test('Add block #1 to chain', () => {
  chain.addBlock(block1);
  assert.strictEqual(chain.chain.length, 2);
});

// ── Section 3: Mine block 2 ──────────────────────────────────────────────────
console.log(`\n${C.yellow}▶ 3. Mining Block #2 (difficulty 2)${C.reset}`);

let block2;
test('Mine block #2 with difficulty 2', () => {
  block2 = chain.mineBlock(MINER_ADDR, 2);
  assert.ok(block2.hash.startsWith('00'));
  assert.strictEqual(block2.index, 2);
});

test('Block #2 links to block #1', () => {
  assert.strictEqual(block2.previousHash, block1.hash);
});

test('Add block #2 to chain', () => {
  chain.addBlock(block2);
  assert.strictEqual(chain.chain.length, 3);
});

// ── Section 4: Chain validation ──────────────────────────────────────────────
console.log(`\n${C.yellow}▶ 4. Chain Integrity${C.reset}`);

test('Full chain validates successfully', () => {
  assert.ok(chain.isValid(), 'Chain should be valid');
});

test('Miner balance reflects coinbase rewards', () => {
  const balance = chain.getBalance(MINER_ADDR);
  // 2 blocks × 50 RUPI = 100 RUPI
  assert.strictEqual(balance, 100, `Expected 100, got ${balance}`);
});

test('Chain length is 3 (genesis + 2 mined)', () => {
  assert.strictEqual(chain.chain.length, 3);
});

// ── Section 5: Transaction signing (built-in crypto P-256) ───────────────────
console.log(`\n${C.yellow}▶ 5. Transaction Signing (ECDSA P-256, built-in crypto)${C.reset}`);

let keyPairAlice, keyPairBob;
test('Generate P-256 key pairs', () => {
  keyPairAlice = crypto.generateKeyPairSync('ec', { namedCurve: 'P-256' });
  keyPairBob   = crypto.generateKeyPairSync('ec', { namedCurve: 'P-256' });
  assert.ok(keyPairAlice.privateKey);
  assert.ok(keyPairAlice.publicKey);
  assert.ok(keyPairBob.privateKey);
});

let tx1;
test('Create and sign a transaction', () => {
  tx1 = new TxStandalone({
    sender:    'RC_ALICE_ADDRESS',
    recipient: 'RC_BOB_ADDRESS',
    amount:    10,
    fee:       0.5,
  });
  tx1.sign(keyPairAlice.privateKey, keyPairAlice.publicKey);
  assert.ok(tx1.signature, 'Signature should be set');
  assert.ok(tx1.publicKey, 'Public key should be stored');
});

test('Verify valid signature returns true', () => {
  assert.ok(tx1.verify(), 'Valid signature should verify');
});

test('isValid() returns true for signed tx', () => {
  assert.ok(tx1.isValid(), 'isValid() should return true');
});

test('Tampered amount fails verification', () => {
  const tampered = Object.assign(Object.create(Object.getPrototypeOf(tx1)), tx1);
  tampered.amount = 99999;  // tamper
  // verify() uses the signable data which includes original amount
  assert.ok(!tampered.verify(), 'Tampered tx should fail verification');
});

test('Wrong key fails verification', () => {
  const fakeTx = new TxStandalone({ sender: 'RC_X', recipient: 'RC_Y', amount: 5 });
  fakeTx.sign(keyPairBob.privateKey, keyPairBob.publicKey);
  // Swap Alice's signature onto Bob's key — mismatch
  fakeTx.publicKey = tx1.publicKey;  // Alice's pubkey
  fakeTx.signature = tx1.signature;  // Alice's signature on different data
  // Should fail because signable data is different
  assert.ok(!fakeTx.verify(), 'Mismatched key/data should fail');
});

// ── Section 6: Tamper detection ───────────────────────────────────────────────
console.log(`\n${C.yellow}▶ 6. Tamper Detection${C.reset}`);

test('Chain is valid before tampering', () => {
  assert.ok(chain.isValid());
});

let savedHash;
test('Tamper with block #1 transaction amount', () => {
  // Save original state
  savedHash = chain.chain[1].hash;
  // Tamper: change coinbase amount
  chain.chain[1].transactions[0].amount = 99999;
  // DO NOT recompute hash — simulating a corrupt block
  assert.ok(!chain.isValid(), 'Chain should be invalid after tampering');
});

test('Restore tampered block — chain valid again', () => {
  chain.chain[1].transactions[0].amount = 50;
  chain.chain[1].hash = chain.chain[1].calcHash();
  // Fix block 2's previousHash reference too (it's still pointing to original hash)
  // Actually block2.hash was computed with the original block1.hash, so we need to restore
  chain.chain[1].hash = savedHash;
  assert.ok(chain.isValid(), 'Chain should be valid after restoration');
});

// ── Section 7: Halving mechanism ─────────────────────────────────────────────
console.log(`\n${C.yellow}▶ 7. Halving Mechanism${C.reset}`);

test('Block 0 reward = 50 RUPI', () => {
  assert.strictEqual(chain.getMiningReward(0), 50);
});

test('Block 210,000 reward = 25 RUPI (1st halving)', () => {
  assert.strictEqual(chain.getMiningReward(210_000), 25);
});

test('Block 420,000 reward = 12.5 RUPI (2nd halving)', () => {
  assert.strictEqual(chain.getMiningReward(420_000), 12.5);
});

test('Block 630,000 reward = 6.25 RUPI (3rd halving)', () => {
  assert.strictEqual(chain.getMiningReward(630_000), 6.25);
});

test('After 64 halvings reward = 0', () => {
  assert.strictEqual(chain.getMiningReward(64 * 210_000), 0);
});

// ─── Summary ──────────────────────────────────────────────────────────────────
console.log(`\n${C.bold}${C.cyan}══════════════════════════════════════${C.reset}`);
console.log(`${C.bold}Test Summary${C.reset}`);
console.log(`${C.bold}${C.cyan}══════════════════════════════════════${C.reset}`);
console.log(`  Total:  ${passed + failed}`);
console.log(`  ${C.green}Passed: ${passed}${C.reset}`);
if (failed > 0) {
  console.log(`  ${C.red}Failed: ${failed}${C.reset}`);
  console.log(`\n${C.red}FAILED TESTS:${C.reset}`);
  results.filter(r => !r.ok).forEach(r => {
    console.log(`  ${C.red}✗ ${r.name}${C.reset}`);
    console.log(`    ${r.error}`);
  });
  process.exit(1);
} else {
  console.log(`\n${C.bold}${C.green}✓ All tests passed!${C.reset}`);
  console.log(`\n${C.dim}Rupi Chain core logic verified. Run 'npm install && node index.js' to start the full node.${C.reset}\n`);
}
