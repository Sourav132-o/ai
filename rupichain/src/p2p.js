'use strict';

/**
 * P2P Network Layer using WebSockets (ws package).
 * Handles peer discovery, block broadcasting, transaction broadcasting,
 * and chain synchronization.
 */

let WebSocket, WebSocketServer;
try {
  ({ WebSocket, WebSocketServer } = require('ws'));
} catch (e) {
  WebSocket = null;
  WebSocketServer = null;
}

const MESSAGE_TYPE = {
  QUERY_LATEST:        'QUERY_LATEST',
  QUERY_ALL:           'QUERY_ALL',
  RESPONSE_BLOCKCHAIN: 'RESPONSE_BLOCKCHAIN',
  NEW_TRANSACTION:     'NEW_TRANSACTION',
  PING:                'PING',
  PONG:                'PONG',
};

class P2PServer {
  constructor(blockchain, port = 6001) {
    this.blockchain = blockchain;
    this.port       = port;
    this.peers      = new Set();   // active WebSocket connections
    this.server     = null;
  }

  start() {
    if (!WebSocketServer) {
      console.warn('[P2P] ws package not installed — P2P disabled. Run: npm install');
      return;
    }

    this.server = new WebSocketServer({ port: this.port });
    this.server.on('connection', (ws, req) => {
      console.log(`[P2P] Incoming connection from ${req.socket.remoteAddress}`);
      this._initConnection(ws);
    });

    console.log(`[P2P] Listening on port ${this.port}`);
  }

  /**
   * Connect to a peer by URL, e.g. "ws://192.168.1.10:6001"
   */
  connectToPeer(peerUrl) {
    if (!WebSocket) {
      console.warn('[P2P] ws package not installed — cannot connect to peer');
      return;
    }
    const ws = new WebSocket(peerUrl);
    ws.on('open',  () => {
      console.log(`[P2P] Connected to peer: ${peerUrl}`);
      this._initConnection(ws);
    });
    ws.on('error', (err) => {
      console.warn(`[P2P] Cannot connect to ${peerUrl}: ${err.message}`);
    });
  }

  _initConnection(ws) {
    this.peers.add(ws);

    ws.on('message', (data) => this._handleMessage(ws, data));
    ws.on('close',   ()     => {
      this.peers.delete(ws);
      console.log('[P2P] Peer disconnected. Total peers:', this.peers.size);
    });
    ws.on('error',   (err)  => {
      console.warn('[P2P] Peer error:', err.message);
      this.peers.delete(ws);
    });

    // Ask the new peer for their latest block
    this._send(ws, { type: MESSAGE_TYPE.QUERY_LATEST });
  }

  _handleMessage(ws, raw) {
    let msg;
    try { msg = JSON.parse(raw); } catch { return; }

    switch (msg.type) {
      case MESSAGE_TYPE.QUERY_LATEST:
        this._send(ws, this._responseLatest());
        break;

      case MESSAGE_TYPE.QUERY_ALL:
        this._send(ws, this._responseAll());
        break;

      case MESSAGE_TYPE.RESPONSE_BLOCKCHAIN:
        this._handleBlockchain(ws, msg.data);
        break;

      case MESSAGE_TYPE.NEW_TRANSACTION:
        this._handleNewTransaction(msg.data);
        break;

      case MESSAGE_TYPE.PING:
        this._send(ws, { type: MESSAGE_TYPE.PONG });
        break;
    }
  }

  _handleBlockchain(ws, receivedBlocks) {
    if (!Array.isArray(receivedBlocks) || receivedBlocks.length === 0) return;

    const latest   = receivedBlocks[receivedBlocks.length - 1];
    const myLatest = this.blockchain.getLatestBlock();

    if (latest.index <= myLatest.index) return;   // we're ahead or equal

    if (latest.previousHash === myLatest.hash) {
      // Next block — try to add it
      try {
        this.blockchain.addBlock(latest);
        console.log(`[P2P] Accepted block #${latest.index} from peer`);
        this._broadcastLatest();
      } catch (err) {
        console.warn('[P2P] Rejected block from peer:', err.message);
      }
    } else if (receivedBlocks.length === 1) {
      // Peer is ahead but we only got one block — ask for full chain
      console.log('[P2P] Peer is ahead — requesting full chain');
      this._send(ws, { type: MESSAGE_TYPE.QUERY_ALL });
    } else {
      // We received a longer chain — attempt replacement
      console.log('[P2P] Received longer chain — attempting replacement');
      const replaced = this.blockchain.replaceChain(receivedBlocks);
      if (replaced) {
        console.log('[P2P] Chain replaced with longer peer chain');
        this._broadcastLatest();
      }
    }
  }

  _handleNewTransaction(txData) {
    if (!txData) return;
    try {
      this.blockchain.addToMempool(txData);
      console.log('[P2P] Transaction added to mempool from peer:', txData.id?.slice(0, 12));
    } catch { /* duplicate or invalid — ignore */ }
  }

  // ---- Broadcast helpers ----

  broadcastTransaction(transaction) {
    this._broadcast({ type: MESSAGE_TYPE.NEW_TRANSACTION, data: transaction });
  }

  _broadcastLatest() {
    this._broadcast(this._responseLatest());
  }

  _broadcast(msg) {
    for (const ws of this.peers) {
      this._send(ws, msg);
    }
  }

  _send(ws, msg) {
    if (ws.readyState === (WebSocket ? WebSocket.OPEN : 1)) {
      try { ws.send(JSON.stringify(msg)); } catch { /* ignore */ }
    }
  }

  // ---- Message factories ----

  _responseLatest() {
    return {
      type: MESSAGE_TYPE.RESPONSE_BLOCKCHAIN,
      data: [this.blockchain.getLatestBlock().toJSON
              ? this.blockchain.getLatestBlock().toJSON()
              : this.blockchain.getLatestBlock()],
    };
  }

  _responseAll() {
    return {
      type: MESSAGE_TYPE.RESPONSE_BLOCKCHAIN,
      data: this.blockchain.toJSON(),
    };
  }

  getPeerCount()  { return this.peers.size; }
  getPeerAddresses() {
    return [...this.peers].map(ws => ws._socket?.remoteAddress || 'unknown');
  }
}

module.exports = { P2PServer, MESSAGE_TYPE };
