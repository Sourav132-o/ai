'use strict';

/**
 * Multi-core CPU Miner
 * Splits nonce range across all available CPU cores using worker_threads.
 * Each worker independently searches its range and reports back.
 */

const { Worker } = require('worker_threads');
const os   = require('os');
const path = require('path');

const WORKER_PATH     = path.join(__dirname, 'miner-worker.js');
const NONCE_CHUNK     = 10_000_000;   // nonces per worker per round
const MAX_NONCE       = 2 ** 32;

class CPUMiner {
  constructor(blockchain) {
    this.blockchain  = blockchain;
    this.numCores    = os.cpus().length;
    this.hashRate    = 0;   // hashes/sec (approximate)
    this._mining     = false;
  }

  /**
   * Mine a single block and return it.
   * @param {string} minerAddress - reward goes here
   * @returns {Promise<Block>}
   */
  async mineBlock(minerAddress) {
    const candidate = this.blockchain.createCandidateBlock(minerAddress);
    const target    = candidate.getTarget();
    const start     = Date.now();

    console.log(`\n[Miner] Mining block #${candidate.index} | diff=${candidate.difficulty} | target="${target}" | cores=${this.numCores}`);

    const header = this._buildHeaderTemplate(candidate);
    let offset   = 0;

    while (offset < MAX_NONCE) {
      const result = await this._runWorkerBatch(header, target, offset);
      if (result) {
        candidate.nonce = result.nonce;
        candidate.hash  = result.hash;

        const elapsed = (Date.now() - start) / 1000;
        const tried   = offset + result.nonce - (offset);
        this.hashRate = Math.round((result.nonce - offset + this.numCores * NONCE_CHUNK / 2) / elapsed);

        console.log(`[Miner] Block #${candidate.index} found! nonce=${result.nonce} hash=${result.hash.slice(0, 16)}... time=${elapsed.toFixed(2)}s`);
        return candidate;
      }
      offset += this.numCores * NONCE_CHUNK;
    }

    throw new Error('Mining failed: nonce space exhausted');
  }

  /**
   * Distribute one batch of nonces across all cores.
   * @returns {Promise<{nonce,hash}|null>}
   */
  _runWorkerBatch(headerTemplate, target, baseOffset) {
    return new Promise((resolve, reject) => {
      const workers  = [];
      let   finished = 0;

      const cleanup = () => workers.forEach(w => w.terminate().catch(() => {}));

      for (let i = 0; i < this.numCores; i++) {
        const startNonce = baseOffset + i * NONCE_CHUNK;
        const endNonce   = startNonce + NONCE_CHUNK - 1;

        const worker = new Worker(WORKER_PATH, {
          workerData: {
            blockHeader: headerTemplate,
            startNonce,
            endNonce,
            target,
            workerId: i,
          },
        });

        workers.push(worker);

        worker.on('message', (msg) => {
          if (msg.found) {
            cleanup();
            resolve({ nonce: msg.nonce, hash: msg.hash });
          } else if (!msg.progress) {
            finished++;
            if (finished === this.numCores) resolve(null);
          }
        });

        worker.on('error', (err) => {
          cleanup();
          reject(err);
        });
      }
    });
  }

  /**
   * Build a JSON string template of the block header (without nonce).
   * Workers will insert the nonce before hashing.
   */
  _buildHeaderTemplate(block) {
    // Replicate the same structure used in Block.calculateHash()
    const txRoot = block._merkleRoot ? block._merkleRoot() : '0'.repeat(64);
    return JSON.stringify({
      index:        block.index,
      timestamp:    block.timestamp,
      txRoot,
      previousHash: block.previousHash,
      nonce:        0,       // workers replace this
      difficulty:   block.difficulty,
      minerAddress: block.minerAddress,
    });
  }

  /**
   * Continuous mining loop — mines block after block.
   * @param {string} minerAddress
   * @param {function} [onBlock] - callback(block) after each block
   */
  async startMining(minerAddress, onBlock) {
    this._mining = true;
    console.log(`[Miner] Starting continuous mining for address: ${minerAddress}`);

    while (this._mining) {
      try {
        const block = await this.mineBlock(minerAddress);
        const added = this.blockchain.addBlock(block);
        console.log(`[Miner] Block #${added.index} added to chain. Height: ${this.blockchain.getHeight()}`);
        if (onBlock) onBlock(added);
      } catch (err) {
        console.error('[Miner] Error:', err.message);
        await new Promise(r => setTimeout(r, 1000));
      }
    }
  }

  stopMining() {
    this._mining = false;
    console.log('[Miner] Mining stopped.');
  }
}

module.exports = { CPUMiner };
