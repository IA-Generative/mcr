/**
 * Browser API polyfills for running the Webex JS SDK in Node.js.
 *
 * Must be required BEFORE importing the SDK. Provides:
 * - WebRTC globals from @roamhq/wrtc (RTCPeerConnection, MediaStream, etc.)
 * - Minimal DOM/browser stubs (document, localStorage, Event, etc.)
 * - getStats() suppression for unimplemented @roamhq/wrtc APIs
 */

const wrtc = require("@roamhq/wrtc");

// ── WebRTC globals (from @roamhq/wrtc) ──────────────────────────────

globalThis.RTCPeerConnection = wrtc.RTCPeerConnection;
globalThis.RTCSessionDescription = wrtc.RTCSessionDescription;
globalThis.RTCIceCandidate = wrtc.RTCIceCandidate;
globalThis.MediaStream = wrtc.MediaStream;
globalThis.MediaStreamTrack = wrtc.MediaStreamTrack;

// ── navigator ────────────────────────────────────────────────────────

globalThis.navigator = globalThis.navigator || {};
globalThis.navigator.mediaDevices = wrtc.mediaDevices;
globalThis.navigator.userAgent =
  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";

// ── window / self ────────────────────────────────────────────────────

globalThis.window = globalThis;
globalThis.self = globalThis;

// ── document (minimal stubs) ─────────────────────────────────────────

globalThis.document = {
  createElement: (tag) => {
    const el = {
      style: {},
      addEventListener: () => {},
      removeEventListener: () => {},
    };
    if (tag === "canvas") {
      el.getContext = () => ({
        drawImage: () => {},
        getImageData: () => ({ data: new Uint8ClampedArray(0) }),
      });
      el.width = 0;
      el.height = 0;
      el.toDataURL = () => "";
    }
    if (tag === "video" || tag === "audio") {
      el.play = () => Promise.resolve();
      el.pause = () => {};
      el.srcObject = null;
      el.muted = false;
      el.volume = 1;
    }
    return el;
  },
  body: { appendChild: () => {}, removeChild: () => {} },
  addEventListener: () => {},
  removeEventListener: () => {},
  hidden: false,
  visibilityState: "visible",
  querySelectorAll: () => [],
  querySelector: () => null,
  head: { appendChild: () => {} },
  documentElement: { style: {} },
};

// ── localStorage ─────────────────────────────────────────────────────

globalThis.localStorage = {
  _data: {},
  getItem(key) { return this._data[key] ?? null; },
  setItem(key, val) { this._data[key] = String(val); },
  removeItem(key) { delete this._data[key]; },
  clear() { this._data = {}; },
};

// ── Event / CustomEvent ──────────────────────────────────────────────

if (!globalThis.Event) {
  globalThis.Event = class Event {
    constructor(type, opts) { this.type = type; Object.assign(this, opts); }
  };
}
if (!globalThis.CustomEvent) {
  globalThis.CustomEvent = class CustomEvent extends globalThis.Event {
    constructor(type, opts) { super(type, opts); this.detail = opts?.detail; }
  };
}

// ── XMLHttpRequest (existence check only) ────────────────────────────

if (!globalThis.XMLHttpRequest) {
  globalThis.XMLHttpRequest = class XMLHttpRequest {
    open() {} send() {} setRequestHeader() {} addEventListener() {}
  };
}

// ── location ─────────────────────────────────────────────────────────

if (!globalThis.location) {
  globalThis.location = { href: "https://localhost", protocol: "https:", hostname: "localhost" };
}

// ── performance ──────────────────────────────────────────────────────

if (!globalThis.performance) {
  globalThis.performance = require("perf_hooks").performance;
}

// ── @roamhq/wrtc getStats() stubs ───────────────────────────────────

const emptyStats = async () => new Map();

const _origGetTransceivers = wrtc.RTCPeerConnection.prototype.getTransceivers;
wrtc.RTCPeerConnection.prototype.getTransceivers = function () {
  const transceivers = _origGetTransceivers.call(this);
  for (const t of transceivers) {
    if (t.sender && !t.sender.getStats) t.sender.getStats = emptyStats;
    if (t.receiver && !t.receiver.getStats) t.receiver.getStats = emptyStats;
  }
  return transceivers;
};

const _origGetSenders = wrtc.RTCPeerConnection.prototype.getSenders;
if (_origGetSenders) {
  wrtc.RTCPeerConnection.prototype.getSenders = function () {
    const senders = _origGetSenders.call(this);
    for (const s of senders) { if (!s.getStats) s.getStats = emptyStats; }
    return senders;
  };
}

const _origGetReceivers = wrtc.RTCPeerConnection.prototype.getReceivers;
if (_origGetReceivers) {
  wrtc.RTCPeerConnection.prototype.getReceivers = function () {
    const receivers = _origGetReceivers.call(this);
    for (const r of receivers) { if (!r.getStats) r.getStats = emptyStats; }
    return receivers;
  };
}

process.on("unhandledRejection", (err) => {
  const msg = err?.message || String(err);
  if (msg.includes("Not yet implemented") || msg.includes("Expected an object")) {
    return;
  }
  console.error("[polyfills] Unhandled rejection:", err);
  process.exit(1);
});

module.exports = { wrtc };
