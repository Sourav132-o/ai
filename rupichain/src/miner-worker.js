'use strict';

/**
 * Miner Worker Thread
 *
 * Receives a range of nonces to search and reports back the first winning nonce,
 * or null if the range is exhausted without finding a solution.
 *
 * Communication via workerData (input) and parentPort.postMessage (output).
 *
 * workerData shape:
 * {
 *   blockHeader : string   – JSON-serialised block header template
 *   startNonce  : number
 *   endNonce    : number
 *   target      : string   – leading-zero prefix the hash must satisfy
 *   workerId    : number   – for logging
 * }
 *
 * postMessage shape (to parent):
 * { found: true,  nonce: number, hash: string }  – when solution found
 * { found: false, workerId: number }              – when range exhausted
 * { progress: true, workerId, nonce }             – periodic progress ping
 */

const { workerData, parentPort } = require('worker_threads');
const crypto = require('crypto');

function doubleSha256(data) {
  const first  = crypto.createHash('sha256').update(data).digest();
  const second = crypto.createHash('sha256').update(first).digest('hex');
  return second;
}

const { blockHeader, startNonce, endNonce, target, workerId } = workerData;

// Parse the header template once
let headerObj;
try {
  headerObj = JSON.parse(blockHeader);
} catch (e) {
  parentPort.postMessage({ found: false, workerId, error: 'Invalid blockHeader JSON' });
  process.exit(1);
}

const PROGRESS_INTERVAL = 500_000;   // report progress every 500k hashes

let nonce = startNonce;

while (nonce <= endNonce) {
  headerObj.nonce = nonce;
  const hash = doubleSha256(JSON.stringify(headerObj));

  if (hash.startsWith(target)) {
    parentPort.postMessage({ found: true, nonce, hash, workerId });
    process.exit(0);
  }

  if ((nonce - startNonce) % PROGRESS_INTERVAL === 0 && nonce !== startNonce) {
    parentPort.postMessage({ progress: true, workerId, nonce });
  }

  nonce++;
}

// Exhausted without finding
parentPort.postMessage({ found: false, workerId });
