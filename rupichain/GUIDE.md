# Rupi Chain — Complete Guide

> **Version:** 2.0.0 | **Node.js:** ≥ 18

---

## 1. What is Rupi Chain?

Rupi Chain is a **Proof-of-Work** cryptocurrency blockchain inspired by Bitcoin's design.
It is written entirely in **Node.js** and built as a learning and experimentation platform.

### Key Features

| Feature | Details |
|---|---|
| **Currency** | RUPI (₹) |
| **Max Supply** | 21,00,000 RUPI |
| **Initial Reward** | 50 RUPI per block |
| **Halving** | Reward halves every 2,10,000 blocks |
| **Block Time** | ~10 seconds (target) |
| **Cryptography** | ECDSA secp256k1 (same as Bitcoin) |
| **Network** | WebSocket P2P |

---

## 2. Installation

### Prerequisites
- **Node.js** 18 or higher
- **npm** (comes with Node.js)

### Windows

```powershell
# Download Node.js from: https://nodejs.org
# Then in PowerShell or CMD:

git clone <repository-url> rupichain
cd rupichain
npm install
node test.js        # run tests (works without npm install)
```

### Linux / Mac

```bash
# Install Node.js (Ubuntu/Debian)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Clone the project
git clone <repository-url> rupichain
cd rupichain
npm install
node test.js
```

---

## 3. Running the Node

### Quick Test (no npm install needed)

```bash
node test.js
```

Uses only Node.js built-in modules and verifies all core logic.

### Start the Full Node

```bash
# Install dependencies
npm install

# Start the node
node index.js
```

On success you will see:
```
╔══════════════════════════════════════════╗
║        Rupi Chain Node v2.0              ║
╠══════════════════════════════════════════╣
║  API:  http://localhost:3001             ║
║  P2P:  ws://localhost:6001               ║
╚══════════════════════════════════════════╝
```

### Custom Ports

```bash
API_PORT=8080 P2P_PORT=7001 node index.js
```

### Web Dashboard

Open in browser: **http://localhost:3001**

---

## 4. Mining

### CLI Miner

```bash
node mine.js RC1A2B3C4D5E6F...   # provide your wallet address
```

### Via Environment Variable

```bash
MINE=true MINER_ADDRESS=RC1A2B3C... node index.js
```

### Multi-Core Mining (automatic)

Rupi Chain automatically uses all available CPU cores:

```javascript
const { CPUMiner } = require('./src/miner');
const miner = new CPUMiner(blockchain);

// Uses os.cpus().length cores automatically
await miner.mineBlock('RC_YOUR_ADDRESS');
```

### GPU Mining

GPU mining is experimental. If hashcat is installed:

```bash
# Check for hashcat
which hashcat
node mine.js RC_ADDRESS  # will attempt to detect GPU automatically
```

Falls back to CPU mining if no GPU is found.

---

## 5. Creating a Wallet

```javascript
// wallet-create.js (create this file)
const { generateWallet } = require('./src/wallet');

const wallet = generateWallet();
console.log('Your new wallet:');
console.log('Address:    ', wallet.address);
console.log('Public Key: ', wallet.publicKey);
console.log('Private Key:', wallet.privateKey);
console.log('\n⚠️  Never share your Private Key!');
```

```bash
node wallet-create.js
```

**Example output:**
```
Address:     RC1A2B3C4D5E6F7890ABCDEF1234567890AB
Public Key:  04abcdef...
Private Key: 8f7a3b...  ← never share this!
```

### Restore Wallet from Private Key

```javascript
const { walletFromPrivateKey } = require('./src/wallet');
const wallet = walletFromPrivateKey('your-private-key-hex');
console.log('Address:', wallet.address);
```

---

## 6. Sending Transactions

### Via JavaScript

```javascript
const { Wallet }      = require('./src/wallet');
const { Transaction } = require('./src/transaction');

const alice = new Wallet('alice-private-key-hex');
const bob   = new Wallet('bob-private-key-hex');

const tx = new Transaction({
  sender:    alice.address,
  recipient: bob.address,
  amount:    10,      // 10 RUPI
  fee:       0.01,    // miner fee
});

alice.signTransaction(tx);
// submit via HTTP API
```

### Via REST API

```bash
curl -X POST http://localhost:3001/transaction \
  -H "Content-Type: application/json" \
  -d '{
    "sender":    "RC_ALICE_ADDRESS",
    "recipient": "RC_BOB_ADDRESS",
    "amount":    10,
    "fee":       0.01,
    "signature": "hex_signature_here",
    "publicKey": "hex_public_key_here",
    "timestamp": 1700000000000
  }'
```

---

## 7. Joining the P2P Network

### Add a Peer

```bash
curl -X POST http://localhost:3001/peers \
  -H "Content-Type: application/json" \
  -d '{"url": "ws://192.168.1.100:6001"}'
```

### Bootstrap Peers via Environment Variable

```bash
PEERS=ws://node1.rupichain.io:6001,ws://node2.rupichain.io:6001 node index.js
```

### Local Testnet (two nodes)

```bash
# Terminal 1
API_PORT=3001 P2P_PORT=6001 node index.js

# Terminal 2
API_PORT=3002 P2P_PORT=6002 PEERS=ws://localhost:6001 node index.js
```

---

## 8. REST API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Web dashboard |
| GET | `/info` | Chain info (height, difficulty, supply) |
| GET | `/chain` | Full blockchain |
| GET | `/blocks/:index` | Block by index |
| GET | `/balance/:address` | Wallet balance |
| POST | `/transaction` | Submit a transaction |
| GET | `/pending` | Mempool (pending transactions) |
| GET | `/mine/:address` | Mine one block (demo) |
| GET | `/peers` | Connected peers list |
| POST | `/peers` | Add a new peer |

---

## 9. Technical Architecture

```
rupichain/
├── index.js              ← main entry point
├── mine.js               ← CLI miner
├── test.js               ← zero-dependency tests (26 pass)
├── package.json
└── src/
    ├── blockchain.js     ← Block, Chain, Mempool logic
    ├── transaction.js    ← secp256k1 transactions
    ├── wallet.js         ← key pair, address generation
    ├── miner.js          ← multi-core CPU miner
    ├── miner-worker.js   ← Worker Thread (hash computation)
    ├── p2p.js            ← WebSocket P2P network
    └── api.js            ← Express REST API + dashboard
```

### Data Flow

```
New block:
Miner → [Worker Thread × N cores] → first winner → Blockchain.addBlock() → P2P broadcast

New transaction:
User → POST /transaction → Mempool → included in next block

P2P sync:
New peer connects → QUERY_LATEST → compare chains → accept longest valid chain
```

### Block Structure

```json
{
  "index":        42,
  "timestamp":    1700000000000,
  "transactions": [...],
  "previousHash": "0000abc...",
  "hash":         "0000def...",
  "nonce":        123456,
  "difficulty":   4,
  "minerAddress": "RC1ABC..."
}
```

### Difficulty Adjustment

- Reviewed every 10 blocks
- Target: one block every 10 seconds
- Blocks too fast → difficulty increases
- Blocks too slow → difficulty decreases

---

## 10. Roadmap

### v2.x (current)
- [x] Proof-of-Work mining
- [x] Multi-core CPU miner
- [x] ECDSA secp256k1 signatures
- [x] P2P WebSocket network
- [x] REST API + dashboard
- [x] Halving mechanism
- [x] Mempool

### v3.x (planned)
- [ ] UTXO model (like Bitcoin)
- [ ] LevelDB persistent storage
- [ ] SPV (Simplified Payment Verification)
- [ ] Full GPU mining support
- [ ] Simple scripting language (smart contracts)
- [ ] Bloom filters
- [ ] Testnet / Mainnet split

---

## 11. Honest Note: How Does Value Come?

This is an important question.

### Reality

Rupi Chain is an **educational project**. To achieve real value like Bitcoin or Ethereum, you need:

1. **Network effect** — thousands of people must actually use it.
2. **Exchange listing** — it must be tradeable on a crypto exchange.
3. **Real utility** — acceptance for goods or services.
4. **Trust** — long-term confidence from users over years.

### Where does cryptocurrency value come from?

```
Value = Network Usage × Trust × Scarcity
```

- **Bitcoin** has value because it has been secure for 15+ years and is used by hundreds of millions of people.
- **New coins** do not become valuable just by writing code.

### Practical Advice

✅ **Good uses:**
- Learning blockchain technology
- Testing private networks
- Practicing DApp development

❌ **Do not:**
- Invest real money into it
- Mislead others by claiming "profitable mining"
- Present it as a real currency

> **Remember:** Always do thorough research before investing in any new crypto project.

---

## 12. Development

### Run Tests

```bash
node test.js    # core logic tests (no npm required)
npm test        # same, via npm script
```

### Reading the Logs

```
[API] REST server running at http://localhost:3001
[P2P] Listening on port 6001
[Miner] Mining block #1 | diff=2 | target="00" | cores=8
[Miner] Block #1 found! nonce=3421 hash=00a3b4c5... time=0.12s
[Node] Block #1 added to chain. Height: 1
```

### Common Issues

| Problem | Solution |
|---------|----------|
| `Cannot find module 'ws'` | Run `npm install` |
| `Cannot find module 'elliptic'` | Run `npm install` |
| Port already in use | `API_PORT=3002 node index.js` |
| Mining too slow | Lower `difficulty` (test only) |

---

## 13. License

This project is for educational purposes. Released under the MIT License.

```
Rupi Chain v2.0.0
Built for learning blockchain technology
```

---

*Last updated: 2026*
