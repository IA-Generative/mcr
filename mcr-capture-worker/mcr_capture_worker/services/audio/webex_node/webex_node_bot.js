#!/usr/bin/env node
/**
 * Webex meeting audio capture bot — runs as a Node.js subprocess.
 *
 * Joins a Webex meeting via the official SDK + @roamhq/wrtc, captures
 * remote audio via RTCAudioSink, encodes to WebM/Opus via FFmpeg, and
 * sends chunks to the parent Python process via stdout.
 *
 * Protocol (stdout, binary frames):
 *   Events:  "E" (1 byte) + 4-byte BE length + JSON bytes
 *   Chunks:  "C" (1 byte) + 4-byte BE length + raw WebM bytes
 *
 * Event payloads:
 *   {"event":"joined"}
 *   {"event":"recording_started"}
 *   {"event":"participants","count":3}
 *   {"event":"recording_stopped"}
 *   {"event":"error","message":"..."}
 *
 * Commands (stdin, line-delimited):
 *   stop — gracefully leave meeting and exit
 *
 * Usage: node webex_node_bot.js <meeting-url> <bot-name>
 */

const { wrtc } = require("./polyfills");
const { RTCAudioSink, RTCAudioSource } = wrtc.nonstandard;

const { spawn } = require("child_process");
const path = require("path");
const readline = require("readline");

const MEETING_URL = process.argv[2];
const BOT_NAME = process.argv[3] || "FCR Agent";
if (!MEETING_URL) {
  process.stderr.write("Usage: node webex_node_bot.js <meeting-url> <bot-name>\n");
  process.exit(1);
}

const CHUNK_DURATION_S = 10;

const WEBEX_GUEST_CLIENT_ID =
  "C64ab04639eefee4798f58e7bc3fe01d47161be0d97ff0d31e040a6ffe66d7f0a";
const WEBEX_GUEST_CLIENT_SECRET =
  "f4261a01a4111b3b3b1710583073cae9cd7104517e7f78800c43d01eea133782";
const WEBEX_TOKEN_ENDPOINT =
  "https://idbroker-guest-k.wbx2.com/idb/oauth2/v1/access_token";

// ── Output helpers ───────────────────────────────────────────────────
// Binary frame protocol: 1-byte type tag + 4-byte BE length + payload
//   "E" = event (JSON), "C" = chunk (raw WebM bytes)

function sendEvent(obj) {
  const payload = Buffer.from(JSON.stringify(obj));
  const header = Buffer.alloc(5);
  header[0] = 0x45; // 'E'
  header.writeUInt32BE(payload.length, 1);
  process.stdout.write(header);
  process.stdout.write(payload);
}

function sendChunk(buf) {
  const header = Buffer.alloc(5);
  header[0] = 0x43; // 'C'
  header.writeUInt32BE(buf.length, 1);
  process.stdout.write(header);
  process.stdout.write(buf);
}

function log(msg) {
  process.stderr.write(`[webex-bot] ${msg}\n`);
}

// ── Guest token fetch ────────────────────────────────────────────────

function parseMeetingUrl(url) {
  const u = new URL(url);
  const match = u.pathname.match(/\/meet\/(?:pr)?(\d+)/);
  if (!match) throw new Error(`Cannot extract meeting key from: ${u.pathname}`);
  return { site: u.hostname, meetingKey: match[1] };
}

async function fetchGuestToken(site, meetingKey, guestName) {
  log("Fetching guest token...");

  const preJoinRes = await fetch(`https://${site}/wbxappapi/v1/preJoin`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      accept: "application/json",
      "spark-user-agent": "webex-js-sdk/3.12.0-next.3 (web)",
      "cisco-no-http-redirect": "true",
    },
    body: JSON.stringify({
      containCCPSetting: true,
      joinTXId: "mcr" + Math.random().toString(36).slice(2, 10),
      guestName,
      supportCheckRequireLogin: true,
      supportGuestCheckCaptcha: true,
      supportU2CV2: false,
      supportHostKey: true,
      supportCountryList: true,
      sipUrl: `${meetingKey}@${site}`,
      locale: "en-US",
    }),
  });
  if (!preJoinRes.ok) throw new Error(`preJoin failed: ${preJoinRes.status}`);
  const { guestJWT } = await preJoinRes.json();
  if (!guestJWT) throw new Error("preJoin response missing guestJWT");

  const { org_id: orgId } = JSON.parse(
    Buffer.from(guestJWT.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"), "base64").toString()
  );

  const tokenRes = await fetch(WEBEX_TOKEN_ENDPOINT, {
    method: "POST",
    headers: {
      "content-type": "application/x-www-form-urlencoded",
      authorization: "Basic " + Buffer.from(`${WEBEX_GUEST_CLIENT_ID}:${WEBEX_GUEST_CLIENT_SECRET}`).toString("base64"),
    },
    body: new URLSearchParams({
      grant_type: "urn:cisco:oauth:grant-type:guest-token",
      scope: "webex-guest:meet_join",
      orgid: orgId,
      client_id: WEBEX_GUEST_CLIENT_ID,
      client_secret: WEBEX_GUEST_CLIENT_SECRET,
      webexapp_jwt: guestJWT,
    }).toString(),
  });
  if (!tokenRes.ok) throw new Error(`access_token failed: ${tokenRes.status}`);
  const { access_token } = await tokenRes.json();
  if (!access_token) throw new Error("No access_token in response");
  log(`Got access token (len=${access_token.length})`);
  return access_token;
}

// ── SDK helpers ──────────────────────────────────────────────────────

function applyMetricsStubs(webex) {
  const noop = () => {};
  if (!webex.internal?.newMetrics) {
    webex.internal.newMetrics = {
      callDiagnosticMetrics: { setDeviceInfo: noop, clearDeviceInfo: noop },
      submitInternalEvent: noop,
      submitClientEvent: noop,
      submitOperationalEvent: noop,
      submitBehavioralEvent: noop,
      submitBusinessEvent: noop,
      submitMQE: noop,
    };
  }
  if (webex.internal?.metrics && !webex.internal.metrics.submitClientMetrics) {
    webex.internal.metrics.submitClientMetrics = noop;
  }
}

function patchH264Sdp() {
  const origSetLocal = RTCPeerConnection.prototype.setLocalDescription;
  RTCPeerConnection.prototype.setLocalDescription = function (desc) {
    if (desc?.sdp?.includes("m=video")) {
      desc = { type: desc.type, sdp: injectFakeH264(desc.sdp) };
    }
    return origSetLocal.call(this, desc);
  };
}

function injectFakeH264(sdp) {
  return sdp.replace(
    /m=video (\d+) (UDP\/TLS\/RTP\/SAVPF)([ \d]+)\r\n/g,
    (match, port, proto, payloads) => {
      if (payloads.includes(" 126")) return match;
      return (
        "m=video " + port + " " + proto + payloads + " 126\r\n" +
        "a=rtpmap:126 H264/90000\r\n" +
        "a=fmtp:126 level-asymmetry-allowed=1;packetization-mode=1;profile-level-id=42e01f\r\n" +
        "a=rtcp-fb:126 nack\r\n"
      );
    }
  );
}

// ── Main ─────────────────────────────────────────────────────────────

async function main() {
  const { site, meetingKey } = parseMeetingUrl(MEETING_URL);
  const accessToken = await fetchGuestToken(site, meetingKey, BOT_NAME);

  let Webex;
  try {
    Webex = require("webex/meetings");
  } catch {
    Webex = require(path.join(__dirname, "node_modules/webex/umd/webex.min.js"));
  }

  const webex = Webex.init({
    credentials: { access_token: accessToken },
    config: { meetings: { experimental: { enableUnifiedMeetings: true } } },
  });

  await new Promise((resolve) => {
    if (webex.canAuthorize) return resolve();
    webex.once("ready", resolve);
  });

  webex.emit("ready");
  await new Promise((r) => setTimeout(r, 0));
  applyMetricsStubs(webex);

  log("Registering meetings plugin...");
  await webex.meetings.register();
  patchH264Sdp();

  const meeting = await webex.meetings.create(MEETING_URL);

  let remoteAudioTrack = null;
  meeting.on("media:ready", (media) => {
    if (media.type === "remoteAudio" && media.stream) {
      const tracks = media.stream.getAudioTracks();
      if (tracks.length > 0) remoteAudioTrack = tracks[0];
    }
  });

  let participantCount = 0;
  meeting.members.on("members:update", (payload) => {
    const members = payload.full ? Object.values(payload.full) : [];
    participantCount = members.filter((m) => m.status === "IN_MEETING").length;
    sendEvent({ event: "participants", count: participantCount });
  });

  // Lobby
  let inLobby = false;
  const admittedPromise = new Promise((resolve) => {
    meeting.on("meeting:self:lobbyWaiting", () => { inLobby = true; log("In lobby..."); });
    meeting.on("meeting:self:guestAdmitted", () => { log("Admitted"); resolve(); });
    meeting.on("media:ready", () => { if (!inLobby) resolve(); });
  });

  log("Joining...");
  await meeting.join({ name: BOT_NAME });

  if (inLobby) {
    await Promise.race([
      admittedPromise,
      new Promise((_, reject) => setTimeout(() => reject(new Error("Lobby timeout (5 min)")), 300000)),
    ]);
  }

  sendEvent({ event: "joined" });

  // Silent audio for sendrecv SDP
  const audioSource = new RTCAudioSource();
  const silentTrack = audioSource.createTrack();
  const silentStream = new MediaStream([silentTrack]);
  const silenceInterval = setInterval(() => {
    audioSource.onData({ samples: new Int16Array(480), sampleRate: 48000, bitsPerSample: 16, channelCount: 1, numberOfFrames: 480 });
  }, 10);

  const origGUM = navigator.mediaDevices.getUserMedia;
  navigator.mediaDevices.getUserMedia = async () => silentStream;

  log("Adding media...");
  await meeting.addMedia({ audioEnabled: true, videoEnabled: false, shareAudioEnabled: false, shareVideoEnabled: false });
  navigator.mediaDevices.getUserMedia = origGUM;

  // Wait for remote audio
  if (!remoteAudioTrack) {
    await new Promise((resolve) => {
      const check = setInterval(() => { if (remoteAudioTrack) { clearInterval(check); resolve(); } }, 500);
      setTimeout(() => { clearInterval(check); resolve(); }, 30000);
    });
  }
  if (!remoteAudioTrack) {
    throw new Error("No remote audio track received");
  }

  // ── Recording: RTCAudioSink → FFmpeg → base64 chunks to stdout ────

  const sink = new RTCAudioSink(remoteAudioTrack);

  // FFmpeg: PCM → WebM/Opus, output to pipe
  const ffmpeg = spawn("ffmpeg", [
    "-f", "s16le", "-ar", "48000", "-ac", "1", "-i", "pipe:0",
    "-c:a", "libopus", "-b:a", "64k",
    "-f", "webm", "pipe:1",
  ], { stdio: ["pipe", "pipe", "pipe"] });

  ffmpeg.stderr.on("data", (d) => {
    const msg = d.toString().trim();
    if (msg) log(`[ffmpeg] ${msg}`);
  });

  sink.ondata = ({ samples }) => {
    if (!ffmpeg.stdin.destroyed) ffmpeg.stdin.write(Buffer.from(samples.buffer));
  };

  // Buffer FFmpeg output and flush as chunks every CHUNK_DURATION_S
  let chunkBuffer = [];
  let chunkBytes = 0;
  ffmpeg.stdout.on("data", (data) => {
    chunkBuffer.push(data);
    chunkBytes += data.length;
  });

  const chunkInterval = setInterval(() => {
    if (chunkBytes > 0) {
      const combined = Buffer.concat(chunkBuffer);
      chunkBuffer = [];
      chunkBytes = 0;
      sendChunk(combined);
    }
  }, CHUNK_DURATION_S * 1000);

  sendEvent({ event: "recording_started" });
  log("Recording...");

  // ── Listen for stop command on stdin ───────────────────────────────

  const rl = readline.createInterface({ input: process.stdin });
  const stopPromise = new Promise((resolve) => {
    rl.on("line", (line) => {
      if (line.trim() === "stop") {
        log("Received stop command");
        resolve();
      }
    });
    rl.on("close", () => resolve());
  });

  await stopPromise;

  // ── Cleanup ────────────────────────────────────────────────────────

  log("Stopping...");
  clearInterval(chunkInterval);
  clearInterval(silenceInterval);
  sink.stop();
  ffmpeg.stdin.end();
  await new Promise((resolve) => ffmpeg.on("close", resolve));

  // Flush remaining buffer
  if (chunkBytes > 0) {
    sendChunk(Buffer.concat(chunkBuffer));
  }

  sendEvent({ event: "recording_stopped" });

  log("Leaving meeting...");
  await meeting.leave().catch((e) => log(`Leave error: ${e.message}`));

  log("Done");
  process.exit(0);
}

main().catch((err) => {
  log(`Fatal: ${err}`);
  sendEvent({ event: "error", message: String(err) });
  process.exit(1);
});
