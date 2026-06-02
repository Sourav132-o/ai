'use strict';

const { Blockchain }   = require('./src/blockchain');
const { P2PServer }    = require('./src/p2p');
const { createApiServer } = require('./src/api');

const API_PORT = parseInt(process.env.API_PORT || '3001', 10);
const P2P_PORT = parseInt(process.env.P2P_PORT || '6001', 10);
const PEERS    = (process.env.PEERS || '').split(',').filter(Boolean);
const MINE     = process.env.MINE === 'true';
const MINER_ADDRESS = process.env.MINER_ADDRESS || 'RC_DEFAULT_MINER';

// ---- Bootstrap ----
const blockchain = new Blockchain();
const p2p        = new P2PServer(blockchain, P2P_PORT);
const app        = createApiServer(blockchain, p2p);

// Start API
app.listen(API_PORT, () => {
  console.log(`
╔══════════════════════════════════════════╗
║        Rupi Chain Node v2.0              ║
╠══════════════════════════════════════════╣
║  API:  http://localhost:${API_PORT}            ║
║  P2P:  ws://localhost:${P2P_PORT}             ║
╚══════════════════════════════════════════╝`);
  console.log(`[Node] Chain height: ${blockchain.getHeight()}`);
  console.log(`[Node] Difficulty:   ${blockchain.getCurrentDifficulty()}`);
});

// Start P2P
p2p.start();

// Connect to bootstrap peers
for (const peer of PEERS) {
  p2p.connectToPeer(peer.trim());
}

// Auto-mine if requested
if (MINE) {
  const { CPUMiner } = require('./src/miner');
  const miner = new CPUMiner(blockchain);
  console.log(`[Node] Auto-mining enabled for address: ${MINER_ADDRESS}`);
  miner.startMining(MINER_ADDRESS, (block) => {
    p2p._broadcastLatest && p2p._broadcastLatest();
  });
}
