'use strict';

/**
 * REST API + HTML Dashboard for Rupi Chain
 */

let express;
try { express = require('express'); } catch { express = null; }

const DASHBOARD_HTML = `<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rupi Chain Explorer</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #0a0e1a; color: #e0e6ff; min-height: 100vh; }
  header { background: linear-gradient(135deg, #1a1f3a, #0d1b2a); padding: 20px 40px; display: flex; align-items: center; gap: 16px; border-bottom: 1px solid #2a3050; }
  header h1 { font-size: 1.6rem; color: #ffd700; letter-spacing: 1px; }
  header p  { font-size: 0.85rem; color: #7a8ab0; margin-top: 4px; }
  .badge { background: #1e3a5f; color: #4fc3f7; padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; }
  main { padding: 30px 40px; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 30px; }
  .stat-card { background: #131929; border: 1px solid #1e2d45; border-radius: 10px; padding: 18px; text-align: center; }
  .stat-card .val { font-size: 1.8rem; font-weight: 700; color: #ffd700; }
  .stat-card .lbl { font-size: 0.75rem; color: #7a8ab0; margin-top: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
  table { width: 100%; border-collapse: collapse; background: #131929; border-radius: 10px; overflow: hidden; }
  th { background: #1a2540; padding: 12px 16px; text-align: left; font-size: 0.78rem; color: #7a8ab0; text-transform: uppercase; letter-spacing: 0.5px; }
  td { padding: 11px 16px; font-size: 0.85rem; border-top: 1px solid #1e2d45; word-break: break-all; }
  tr:hover td { background: #1a2540; }
  .hash { font-family: monospace; color: #4fc3f7; font-size: 0.8rem; }
  .section-title { font-size: 1.1rem; color: #b0c4de; margin: 24px 0 12px; }
  .api-box { background: #131929; border: 1px solid #1e2d45; border-radius: 10px; padding: 20px; font-family: monospace; font-size: 0.82rem; line-height: 1.8; color: #90b4ce; }
  .method-get  { color: #4caf50; }
  .method-post { color: #ff9800; }
</style>
</head>
<body>
<header>
  <div>
    <h1>&#9672; Rupi Chain Explorer</h1>
    <p>Live Blockchain Dashboard &nbsp;<span class="badge">v2.0</span></p>
  </div>
</header>
<main>
  <div class="stats" id="stats">
    <div class="stat-card"><div class="val" id="s-height">...</div><div class="lbl">Block Height</div></div>
    <div class="stat-card"><div class="val" id="s-diff">...</div><div class="lbl">Difficulty</div></div>
    <div class="stat-card"><div class="val" id="s-supply">...</div><div class="lbl">Total Supply (RUPI)</div></div>
    <div class="stat-card"><div class="val" id="s-reward">...</div><div class="lbl">Block Reward</div></div>
    <div class="stat-card"><div class="val" id="s-pending">...</div><div class="lbl">Pending Txns</div></div>
    <div class="stat-card"><div class="val" id="s-peers">...</div><div class="lbl">Peers</div></div>
  </div>

  <p class="section-title">Latest Blocks</p>
  <table>
    <thead><tr><th>#</th><th>Hash</th><th>Miner</th><th>Txns</th><th>Nonce</th><th>Time</th></tr></thead>
    <tbody id="blocks-body"><tr><td colspan="6" style="text-align:center;color:#555">Loading...</td></tr></tbody>
  </table>

  <p class="section-title">API Endpoints</p>
  <div class="api-box">
    <span class="method-get">GET</span>  /chain            — Full blockchain<br>
    <span class="method-get">GET</span>  /blocks/:index    — Block by index<br>
    <span class="method-get">GET</span>  /balance/:address — Wallet balance<br>
    <span class="method-get">GET</span>  /pending          — Mempool transactions<br>
    <span class="method-get">GET</span>  /info             — Chain info<br>
    <span class="method-get">GET</span>  /peers            — Connected peers<br>
    <span class="method-post">POST</span> /transaction      — Submit transaction (JSON body)<br>
    <span class="method-get">GET</span>  /mine/:address    — Mine one block (demo)<br>
  </div>
</main>
<script>
async function load() {
  try {
    const info = await fetch('/info').then(r => r.json());
    document.getElementById('s-height').textContent  = info.height;
    document.getElementById('s-diff').textContent    = info.difficulty;
    document.getElementById('s-supply').textContent  = info.totalSupply.toFixed(2);
    document.getElementById('s-reward').textContent  = info.miningReward;
    document.getElementById('s-pending').textContent = info.pendingTransactions;
    document.getElementById('s-peers').textContent   = info.peers;
  } catch {}

  try {
    const chain = await fetch('/chain').then(r => r.json());
    const tbody = document.getElementById('blocks-body');
    const latest = chain.slice(-10).reverse();
    tbody.innerHTML = latest.map(b => {
      const t = new Date(b.timestamp).toLocaleTimeString();
      const miner = (b.minerAddress || 'GENESIS').slice(0, 16) + '...';
      const hash  = b.hash.slice(0, 20) + '...';
      return \`<tr><td>\${b.index}</td><td class="hash">\${hash}</td><td>\${miner}</td><td>\${b.transactions.length}</td><td>\${b.nonce}</td><td>\${t}</td></tr>\`;
    }).join('');
  } catch {}
}
load();
setInterval(load, 5000);
</script>
</body>
</html>`;

function createApiServer(blockchain, p2pServer) {
  if (!express) {
    console.warn('[API] express package not installed — API disabled. Run: npm install');
    return { listen: () => {} };
  }

  const app = express();
  app.use(express.json());

  // CORS for dev
  app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Headers', 'Content-Type');
    next();
  });

  // ---- Dashboard ----
  app.get('/', (req, res) => res.send(DASHBOARD_HTML));

  // ---- Chain info ----
  app.get('/info', (req, res) => {
    const height = blockchain.getHeight();
    res.json({
      name:                'Rupi Chain',
      version:             '2.0.0',
      height,
      difficulty:          blockchain.getCurrentDifficulty(),
      totalSupply:         blockchain.getTotalSupply(),
      miningReward:        blockchain.getMiningReward(height + 1),
      pendingTransactions: blockchain.mempool.length,
      peers:               p2pServer ? p2pServer.getPeerCount() : 0,
      latestHash:          blockchain.getLatestBlock().hash,
    });
  });

  // ---- Full chain ----
  app.get('/chain', (req, res) => {
    res.json(blockchain.toJSON());
  });

  // ---- Block by index ----
  app.get('/blocks/:index', (req, res) => {
    const idx = parseInt(req.params.index, 10);
    if (isNaN(idx) || idx < 0 || idx >= blockchain.chain.length) {
      return res.status(404).json({ error: 'Block not found' });
    }
    const b = blockchain.chain[idx];
    res.json(b.toJSON ? b.toJSON() : b);
  });

  // ---- Balance ----
  app.get('/balance/:address', (req, res) => {
    const balance = blockchain.getBalance(req.params.address);
    res.json({ address: req.params.address, balance });
  });

  // ---- Mempool ----
  app.get('/pending', (req, res) => {
    res.json(blockchain.getPendingTransactions());
  });

  // ---- Submit transaction ----
  app.post('/transaction', (req, res) => {
    try {
      blockchain.addToMempool(req.body);
      if (p2pServer) p2pServer.broadcastTransaction(req.body);
      res.json({ success: true, id: req.body.id });
    } catch (err) {
      res.status(400).json({ error: err.message });
    }
  });

  // ---- Mine one block (demo/dev) ----
  app.get('/mine/:address', async (req, res) => {
    try {
      const { CPUMiner } = require('./miner');
      const miner = new CPUMiner(blockchain);
      const block = await miner.mineBlock(req.params.address);
      const added = blockchain.addBlock(block);
      if (p2pServer) p2pServer._broadcastLatest();
      res.json({ success: true, block: added.toJSON ? added.toJSON() : added });
    } catch (err) {
      res.status(500).json({ error: err.message });
    }
  });

  // ---- Connect peer ----
  app.post('/peers', (req, res) => {
    const { url } = req.body;
    if (!url) return res.status(400).json({ error: 'url required' });
    if (p2pServer) {
      p2pServer.connectToPeer(url);
      res.json({ success: true, message: `Connecting to ${url}` });
    } else {
      res.status(503).json({ error: 'P2P server not running' });
    }
  });

  // ---- Peer list ----
  app.get('/peers', (req, res) => {
    res.json({
      count:   p2pServer ? p2pServer.getPeerCount() : 0,
      peers:   p2pServer ? p2pServer.getPeerAddresses() : [],
    });
  });

  return app;
}

module.exports = { createApiServer };
