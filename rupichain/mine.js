'use strict';

/**
 * CLI Mining Script
 * Usage: node mine.js <wallet-address>
 *   or:  MINER_ADDRESS=RC... node mine.js
 */

const { Blockchain } = require('./src/blockchain');
const { CPUMiner }   = require('./src/miner');

const address = process.argv[2] || process.env.MINER_ADDRESS;

if (!address) {
  console.error('Usage: node mine.js <your-wallet-address>');
  console.error('Example: node mine.js RC1A2B3C4D5E6F...');
  process.exit(1);
}

const blockchain = new Blockchain();
const miner      = new CPUMiner(blockchain);

console.log(`[Mine CLI] Rupi Chain Miner`);
console.log(`[Mine CLI] Address: ${address}`);
console.log(`[Mine CLI] CPU Cores: ${require('os').cpus().length}`);
console.log('[Mine CLI] Press Ctrl+C to stop\n');

miner.startMining(address, (block) => {
  const reward = block.transactions.find(tx => tx.type === 'coinbase');
  console.log(`[Mine CLI] Earned: ${reward ? reward.amount : 0} RUPI | Total blocks: ${blockchain.getHeight()}`);
});
