# Rupi Chain v2.0 — সম্পূর্ণ বাংলা গাইড

## কী এই Rupi Chain?

Rupi Chain হলো একটি সম্পূর্ণ ব্লকচেইন সিস্টেম যা Bitcoin-এর মতো একই প্রযুক্তিতে তৈরি। এটি একটি শেখার ও পরীক্ষার প্ল্যাটফর্ম, তবে এর ভিত্তি সম্পূর্ণ আসল।

### মূল বৈশিষ্ট্য

| বৈশিষ্ট্য | বিবরণ |
|-----------|-------|
| **Proof of Work** | Bitcoin-এর মতো mining |
| **Multi-core CPU Mining** | আপনার সব CPU core একসাথে কাজ করে |
| **secp256k1 ECDSA** | Bitcoin/Ethereum-এর আসল cryptography |
| **Auto Difficulty** | প্রতি ১০ ব্লকে নিজেই কঠিন/সহজ করে |
| **Halving** | প্রতি ২,১০,০০০ ব্লকে reward অর্ধেক |
| **P2P Network** | একাধিক কম্পিউটার যুক্ত হতে পারে |
| **Web Dashboard** | ব্রাউজারে দেখুন |
| **Wallet System** | RC... ঠিকানা ফরম্যাট |

---

## ইনস্টলেশন

### ধাপ ১: Node.js ইনস্টল করুন

**Windows:**
1. https://nodejs.org → "LTS" বোতামে ক্লিক
2. ডাউনলোড করে চালান
3. PC রিস্টার্ট করুন
4. Command Prompt খুলুন: `node --version` টাইপ করুন (v18+ দেখাবে)

**Linux (Ubuntu/Debian):**
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**Mac:**
```bash
brew install node
```

### ধাপ ২: ফোল্ডার প্রস্তুত করুন

**Windows:**
```
rupichain ফোল্ডারটি C:\rupichain এ রাখুন
Command Prompt:
  cd C:\rupichain
  npm install
```

**Linux/Mac:**
```bash
cd rupichain
npm install
```

---

## প্রথমবার চালানো

### Test (কোনো ইনস্টল ছাড়াই)
```bash
node test.js
```
এটি শুধু Node.js built-in দিয়ে চলে — mining, signature, tamper detection সব পরীক্ষা করে।

### Node চালু করুন
```bash
node index.js
```
তারপর ব্রাউজারে: **http://localhost:3001**

### Mining শুরু করুন
```bash
node mine.js RC1A2B3C4D5E6F7890ABCDEF1234
```
আপনার wallet address দিন।

---

## Wallet তৈরি করুন

npm install করার পর:
```javascript
// wallet-create.js
const { generateWallet } = require('./src/wallet');
const w = generateWallet();
console.log('Address:     ', w.address);
console.log('Public Key:  ', w.publicKey);
console.log('Private Key: ', w.privateKey);
// ⚠️ Private key সংরক্ষণ করুন — হারালে টাকা হারাবেন!
```
```bash
node wallet-create.js
```

---

## Transaction পাঠানো

### API দিয়ে (REST)
```bash
curl -X POST http://localhost:3001/transaction \
  -H "Content-Type: application/json" \
  -d '{"sender":"RCABC...","recipient":"RCDEF...","amount":5,"fee":0.1}'
```

### Code দিয়ে
```javascript
const { generateWallet } = require('./src/wallet');
const { Transaction }    = require('./src/transaction');
const { Blockchain }     = require('./src/blockchain');

const blockchain = new Blockchain();
const alice = generateWallet();
const bob   = generateWallet();

const tx = new Transaction({
  sender:    alice.address,
  recipient: bob.address,
  amount:    10,
  fee:       0.1,
});
alice.signTransaction(tx);

blockchain.addToMempool(tx);
console.log('Transaction added!', tx.id);
```

---

## P2P নেটওয়ার্কে যুক্ত হওয়া

### নতুন peer যুক্ত করুন
```bash
curl -X POST http://localhost:3001/peers \
  -H "Content-Type: application/json" \
  -d '{"url":"ws://192.168.1.10:6001"}'
```

### অথবা startup এ
```bash
PEERS=ws://192.168.1.10:6001,ws://192.168.1.11:6001 node index.js
```

### Environment Variables
| Variable | Default | বিবরণ |
|----------|---------|-------|
| `API_PORT` | 3001 | REST API পোর্ট |
| `P2P_PORT` | 6001 | P2P WebSocket পোর্ট |
| `PEERS` | (empty) | comma-separated peer URLs |
| `MINE` | false | `true` হলে auto-mining চালু |
| `MINER_ADDRESS` | RC_DEFAULT... | mining reward যাবে কোথায় |

---

## API Endpoints

| Method | URL | কাজ |
|--------|-----|-----|
| GET | `/` | Web dashboard |
| GET | `/info` | Chain info |
| GET | `/chain` | পুরো blockchain |
| GET | `/blocks/:n` | n নম্বর block |
| GET | `/balance/:address` | Wallet balance |
| GET | `/pending` | Mempool |
| POST | `/transaction` | Transaction জমা দিন |
| GET | `/mine/:address` | এক ব্লক mine করুন (dev) |
| GET | `/peers` | Connected peers |
| POST | `/peers` | নতুন peer যোগ করুন |

---

## Technical Architecture

```
rupichain/
├── index.js              ← Main entry point
├── mine.js               ← CLI miner
├── test.js               ← Zero-dependency tests
├── package.json
├── GUIDE.md
└── src/
    ├── blockchain.js     ← Block + Chain + Mempool
    ├── transaction.js    ← ECDSA secp256k1 transactions
    ├── wallet.js         ← Key generation + Address
    ├── miner.js          ← Multi-core CPU miner
    ├── miner-worker.js   ← Worker thread (1 per CPU core)
    ├── p2p.js            ← WebSocket P2P network
    └── api.js            ← Express REST API + Dashboard
```

### কীভাবে Mining কাজ করে

```
আপনার CPU: 8 cores
  Core 0: nonce 0       → 10,000,000
  Core 1: nonce 10M     → 20,000,000
  Core 2: nonce 20M     → 30,000,000
  ...
  কোনো একটি core সঠিক hash খুঁজে পেলে বাকিরা থামে
```

### Proof of Work

Block hash-কে এই শর্ত মানতে হবে:
```
difficulty=3 → hash শুরু হবে "000..." দিয়ে
difficulty=4 → hash শুরু হবে "0000..." দিয়ে
```

প্রতি ১০ ব্লকে সময় মাপা হয়:
- ১০ সেকেন্ডের চেয়ে বেশি সময় → difficulty কমবে
- ১০ সেকেন্ডের কম সময় → difficulty বাড়বে

### Halving Schedule

| Block | Reward |
|-------|--------|
| 0 | 50 RUPI |
| 210,000 | 25 RUPI |
| 420,000 | 12.5 RUPI |
| 630,000 | 6.25 RUPI |
| ... | ... |
| সর্বোচ্চ supply | ~10,500,000 RUPI |

---

## সততার সাথে কিছু কথা

### RAM/APU mining প্রসঙ্গে
RAM শুধু ডেটা সংরক্ষণ করে, হিসাব করে না। Blockchain mining মানে হলো অনেক SHA-256 হ্যাশ গণনা করা — এটা করে CPU এবং GPU। এই কোড আপনার **সব CPU core** ব্যবহার করে।

### মূল্য কীভাবে আসে?
কোড লিখলেই মূল্য আসে না। Bitcoin-এর মূল্য এসেছে:
1. **সময়** — ২০০৯ থেকে ধীরে ধীরে
2. **ব্যবহার** — মানুষ সত্যিকারের কাজে লাগিয়েছে
3. **বিশ্বাস** — হাজার হাজার মানুষ একমত হয়েছে
4. **নিরাপত্তা** — বছরের পর বছর ধরে পরীক্ষিত

এই কোডটি একটি **শক্তিশালী ভিত্তি** — কিন্তু উপরের সবগুলো আপনাকেই তৈরি করতে হবে।

---

## Roadmap (পরবর্তী ধাপ)

- [ ] Smart contracts (EVM বা নিজস্ব VM)
- [ ] Light wallet (mobile)
- [ ] Block explorer website
- [ ] Testnet deployment
- [ ] Community building
- [ ] Exchange listing (অনেক পরে)

---

*Rupi Chain v2.0 — Built with Node.js*
