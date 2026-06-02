# রুপি চেইন (Rupi Chain) — সম্পূর্ণ গাইড

> **ভাষা:** বাংলা | **Version:** 2.0.0 | **Node.js:** ≥ 18

---

## ১. কী এই Rupi Chain?

Rupi Chain হলো একটি **Proof-of-Work** ভিত্তিক ক্রিপ্টোকারেন্সি ব্লকচেইন, যা Bitcoin-এর নকশায় অনুপ্রাণিত।  
এটি সম্পূর্ণ **Node.js** তে লেখা এবং শেখার উদ্দেশ্যে তৈরি।

### মূল বৈশিষ্ট্যসমূহ:
| বৈশিষ্ট্য | বিবরণ |
|---|---|
| **মুদ্রার নাম** | RUPI (₹) |
| **মোট সরবরাহ** | ২১,০০,০০০ RUPI |
| **প্রথম পুরস্কার** | ৫০ RUPI প্রতি ব্লক |
| **হালভিং** | প্রতি ২,১০,০০০ ব্লকে পুরস্কার অর্ধেক |
| **ব্লক সময়** | ~১০ সেকেন্ড (লক্ষ্য) |
| **ক্রিপ্টোগ্রাফি** | ECDSA secp256k1 (Bitcoin-এর মতো) |
| **নেটওয়ার্ক** | WebSocket P2P |

---

## ২. ইনস্টলেশন

### পূর্বশর্ত
- **Node.js** ১৮ বা তার বেশি
- **npm** (Node.js এর সাথে আসে)

### Windows-এ ইনস্টলেশন

```powershell
# Node.js ডাউনলোড করুন: https://nodejs.org
# তারপর PowerShell বা CMD-এ:

git clone <repository-url> rupichain
cd rupichain
npm install
node test.js        # পরীক্ষা চালান (কোনো npm install ছাড়াই কাজ করবে)
```

### Linux/Mac-এ ইনস্টলেশন

```bash
# Node.js ইনস্টল করুন (Ubuntu/Debian)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# প্রকল্প ক্লোন করুন
git clone <repository-url> rupichain
cd rupichain
npm install
node test.js
```

---

## ৩. কীভাবে চালাবেন

### প্রথমে পরীক্ষা করুন (npm ছাড়া)

```bash
node test.js
```

এটি শুধুমাত্র Node.js built-in মডিউল ব্যবহার করে এবং সব মূল লজিক পরীক্ষা করে।

### পূর্ণ নোড চালু করুন

```bash
# ডিপেন্ডেন্সি ইনস্টল করুন
npm install

# নোড চালু করুন
node index.js
```

সফলভাবে চালু হলে দেখতে পাবেন:
```
╔══════════════════════════════════════════╗
║        Rupi Chain Node v2.0              ║
╠══════════════════════════════════════════╣
║  API:  http://localhost:3001             ║
║  P2P:  ws://localhost:6001               ║
╚══════════════════════════════════════════╝
```

### কাস্টম পোর্টে চালান

```bash
API_PORT=8080 P2P_PORT=7001 node index.js
```

### ওয়েব ড্যাশবোর্ড

ব্রাউজারে খুলুন: **http://localhost:3001**

---

## ৪. Mining শুরু করবেন কীভাবে

### CLI মাইনার

```bash
node mine.js RC1A2B3C4D5E6F...   # আপনার ওয়ালেট অ্যাড্রেস দিন
```

### এনভায়রনমেন্ট ভেরিয়েবল দিয়ে

```bash
MINE=true MINER_ADDRESS=RC1A2B3C... node index.js
```

### মাল্টি-কোর মাইনিং (স্বয়ংক্রিয়)

Rupi Chain স্বয়ংক্রিয়ভাবে আপনার সব CPU কোর ব্যবহার করে:

```javascript
// src/miner.js ব্যবহার করে
const { CPUMiner } = require('./src/miner');
const miner = new CPUMiner(blockchain);

// os.cpus().length কোর স্বয়ংক্রিয়ভাবে ব্যবহার হয়
await miner.mineBlock('RC_YOUR_ADDRESS');
```

### GPU মাইনিং

GPU মাইনিং এখনো পরীক্ষামূলক। যদি hashcat ইনস্টল থাকে:

```bash
# hashcat-এর মাধ্যমে (ভবিষ্যৎ সংস্করণে পূর্ণ সমর্থন)
which hashcat   # পরীক্ষা করুন
node mine.js RC_ADDRESS  # স্বয়ংক্রিয়ভাবে GPU খোঁজার চেষ্টা করবে
```

GPU না পাওয়া গেলে স্বয়ংক্রিয়ভাবে CPU mining-এ ফিরে যাবে।

---

## ৫. Wallet তৈরি

```javascript
// wallet-create.js (নতুন ফাইল তৈরি করুন)
const { generateWallet } = require('./src/wallet');

const wallet = generateWallet();
console.log('আপনার নতুন ওয়ালেট:');
console.log('Address:    ', wallet.address);
console.log('Public Key: ', wallet.publicKey);
console.log('Private Key:', wallet.privateKey);
console.log('\n⚠️  Private Key সবসময় গোপন রাখুন!');
```

```bash
node wallet-create.js
```

**উদাহরণ আউটপুট:**
```
Address:     RC1A2B3C4D5E6F7890ABCDEF1234567890AB
Public Key:  04abcdef...
Private Key: 8f7a3b...  ← এটি কখনো শেয়ার করবেন না!
```

### বিদ্যমান Private Key থেকে ওয়ালেট পুনরুদ্ধার

```javascript
const { walletFromPrivateKey } = require('./src/wallet');
const wallet = walletFromPrivateKey('your-private-key-hex');
console.log('Address:', wallet.address);
```

---

## ৬. Transaction পাঠানো

### JavaScript কোডের মাধ্যমে

```javascript
const { Wallet } = require('./src/wallet');
const { Transaction } = require('./src/transaction');

// ওয়ালেট লোড করুন
const alice = new Wallet('alice-private-key-hex');
const bob   = new Wallet('bob-private-key-hex');

// ট্রানজেকশন তৈরি করুন
const tx = new Transaction({
  sender:    alice.address,
  recipient: bob.address,
  amount:    10,      // ১০ RUPI
  fee:       0.01,    // মাইনার ফি
});

// সই করুন
alice.signTransaction(tx);

// নেটওয়ার্কে পাঠান (HTTP API)
```

### REST API-এর মাধ্যমে

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

## ৭. P2P নেটওয়ার্কে যুক্ত হওয়া

### পিয়ার যোগ করুন

```bash
# চলমান নোডে পিয়ার যোগ করুন
curl -X POST http://localhost:3001/peers \
  -H "Content-Type: application/json" \
  -d '{"url": "ws://192.168.1.100:6001"}'
```

### পরিবেশ ভেরিয়েবল দিয়ে বুটস্ট্র্যাপ পিয়ার

```bash
PEERS=ws://node1.rupichain.io:6001,ws://node2.rupichain.io:6001 node index.js
```

### লোকাল টেস্টনেট (দুটি নোড)

```bash
# টার্মিনাল ১
API_PORT=3001 P2P_PORT=6001 node index.js

# টার্মিনাল ২  
API_PORT=3002 P2P_PORT=6002 PEERS=ws://localhost:6001 node index.js
```

---

## ৮. REST API রেফারেন্স

| Method | Endpoint | বিবরণ |
|--------|----------|-------|
| GET | `/` | ওয়েব ড্যাশবোর্ড |
| GET | `/info` | চেইন তথ্য (উচ্চতা, কঠিনতা, সরবরাহ) |
| GET | `/chain` | সম্পূর্ণ ব্লকচেইন |
| GET | `/blocks/:index` | নির্দিষ্ট ব্লক |
| GET | `/balance/:address` | ওয়ালেট ব্যালেন্স |
| POST | `/transaction` | ট্রানজেকশন জমা দিন |
| GET | `/pending` | মেমপুল (অপেক্ষমাণ ট্রানজেকশন) |
| GET | `/mine/:address` | একটি ব্লক মাইন করুন (ডেমো) |
| GET | `/peers` | সংযুক্ত পিয়ার তালিকা |
| POST | `/peers` | নতুন পিয়ার যোগ করুন |

---

## ৯. প্রযুক্তিগত আর্কিটেকচার

```
rupichain/
├── index.js              ← মূল এন্ট্রি পয়েন্ট
├── mine.js               ← CLI মাইনার
├── test.js               ← স্বনির্ভর পরীক্ষা (কোনো npm ছাড়া)
├── package.json
└── src/
    ├── blockchain.js     ← ব্লক, চেইন, মেমপুল লজিক
    ├── transaction.js    ← secp256k1 ট্রানজেকশন
    ├── wallet.js         ← কী পেয়ার, অ্যাড্রেস জেনারেশন
    ├── miner.js          ← মাল্টি-কোর CPU মাইনার
    ├── miner-worker.js   ← Worker Thread (হ্যাশ কম্পিউটেশন)
    ├── p2p.js            ← WebSocket P2P নেটওয়ার্ক
    └── api.js            ← Express REST API + ড্যাশবোর্ড
```

### ডেটা ফ্লো

```
নতুন ব্লক খোঁজা:
Miner → [Worker Thread x N কোর] → প্রথম জয়ী → Blockchain.addBlock() → P2P broadcast

নতুন ট্রানজেকশন:
User → POST /transaction → Mempool → পরবর্তী ব্লকে অন্তর্ভুক্ত

P2P সিঙ্ক:
নতুন পিয়ার সংযোগ → QUERY_LATEST → চেইন তুলনা → দীর্ঘতম বৈধ চেইন গ্রহণ
```

### ব্লক স্ট্রাকচার

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

- প্রতি ১০ ব্লকে কঠিনতা পর্যালোচনা হয়
- লক্ষ্য: প্রতি ১০ সেকেন্ডে একটি ব্লক
- যদি ব্লক খুব দ্রুত হয় → কঠিনতা বাড়ে
- যদি ব্লক খুব ধীর হয় → কঠিনতা কমে

---

## ১০. Roadmap

### সংস্করণ 2.x (বর্তমান)
- [x] Proof-of-Work মাইনিং
- [x] মাল্টি-কোর CPU মাইনার
- [x] ECDSA secp256k1 সিগনেচার
- [x] P2P WebSocket নেটওয়ার্ক
- [x] REST API + ড্যাশবোর্ড
- [x] হালভিং মেকানিজম
- [x] মেমপুল

### সংস্করণ 3.x (পরিকল্পিত)
- [ ] UTXO মডেল (Bitcoin-এর মতো)
- [ ] LevelDB persistent storage
- [ ] SPV (Simplified Payment Verification)
- [ ] পূর্ণ GPU মাইনিং সমর্থন
- [ ] Script ভাষা (simple smart contracts)
- [ ] Bloom filters
- [ ] Testnet/Mainnet বিভাজন

---

## ১১. সততার সাথে: মূল্য কীভাবে আসে?

এটি একটি গুরুত্বপূর্ণ প্রশ্ন।

### বাস্তবতা

Rupi Chain একটি **শিক্ষামূলক প্রকল্প**। Bitcoin বা Ethereum-এর মতো "মূল্য" পেতে হলে এগুলো লাগবে:

1. **নেটওয়ার্ক ইফেক্ট:** হাজার হাজার লোক এটি ব্যবহার করতে হবে।
2. **এক্সচেঞ্জ লিস্টিং:** কোনো ক্রিপ্টো এক্সচেঞ্জে ট্রেড হতে হবে।
3. **প্রকৃত ব্যবহার:** কোনো পণ্য বা সেবার জন্য গ্রহণযোগ্যতা।
4. **বিশ্বাস:** ব্যবহারকারীদের দীর্ঘমেয়াদী আস্থা।

### ক্রিপ্টোকারেন্সির মূল্য কোথা থেকে আসে?

```
মূল্য = নেটওয়ার্ক ব্যবহার × বিশ্বাস × ঘাটতি
```

- **Bitcoin** মূল্যবান কারণ ১৫+ বছর ধরে নিরাপদ এবং কোটি কোটি মানুষ ব্যবহার করে।
- **নতুন কয়েন** শুধু কোড লিখলেই মূল্যবান হয় না।

### ব্যবহারিক পরামর্শ

✅ **ব্যবহার করুন:**  
- ব্লকচেইন শেখার জন্য
- প্রাইভেট নেটওয়ার্ক পরীক্ষার জন্য
- DApp ডেভেলপমেন্ট শেখার জন্য

❌ **করবেন না:**  
- বাস্তব অর্থ বিনিয়োগ করবেন না
- অন্যদের "লাভজনক মাইনিং" বলে প্রতারণা করবেন না
- এটিকে বাস্তব মুদ্রা হিসেবে উপস্থাপন করবেন না

> **মনে রাখুন:** যেকোনো নতুন ক্রিপ্টো প্রজেক্টে বিনিয়োগ করার আগে সম্পূর্ণ গবেষণা করুন।

---

## ১২. ডেভেলপমেন্ট

### পরীক্ষা চালান

```bash
node test.js          # কোর লজিক পরীক্ষা (npm ছাড়া)
npm test              # একই, npm script হিসেবে
```

### লগগুলো বোঝা

```
[API] REST server running at http://localhost:3001
[P2P] Listening on port 6001
[Miner] Mining block #1 | diff=2 | target="00" | cores=8
[Miner] Block #1 found! nonce=3421 hash=00a3b4c5... time=0.12s
[Node] Block #1 added to chain. Height: 1
```

### কমন সমস্যা

| সমস্যা | সমাধান |
|--------|--------|
| `Cannot find module 'ws'` | `npm install` চালান |
| `Cannot find module 'elliptic'` | `npm install` চালান |
| Port already in use | `API_PORT=3002 node index.js` |
| Mining too slow | `difficulty` কমান (test only) |

---

## ১৩. লাইসেন্স এবং যোগাযোগ

এই প্রকল্পটি শিক্ষামূলক উদ্দেশ্যে তৈরি। MIT License এর অধীনে।

```
Rupi Chain v2.0.0
Built with ❤️ for learning blockchain technology
```

---

*শেষ আপডেট: ২০২৬*
