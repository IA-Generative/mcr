;(function () {
  const NativeRTCPeerConnection = window.RTCPeerConnection;
  if (!NativeRTCPeerConnection) return;

  // ═══════════════════════════════════════════════════════════════════════
  // Layer 1 — Track Interception
  // ═══════════════════════════════════════════════════════════════════════

  const interceptedConnections = [];
  const audioTracks = [];
  const seenTrackIds = new Set();

  function onRemoteAudioTrack(track) {
    if (track.kind !== "audio" || seenTrackIds.has(track.id)) return;
    seenTrackIds.add(track.id);
    audioTracks.push(track);
  }

  function interceptPeerConnections(onAudioTrack) {
    window.RTCPeerConnection = function (...args) {
      const pc = new NativeRTCPeerConnection(...args);
      interceptedConnections.push(pc);
      pc.addEventListener("track", (e) => onAudioTrack(e.track));
      return pc;
    };
    window.RTCPeerConnection.prototype = NativeRTCPeerConnection.prototype;
  }

  function interceptSrcObjectSetter(onAudioTrack) {
    const nativeDesc = Object.getOwnPropertyDescriptor(
      HTMLMediaElement.prototype, "srcObject"
    );
    if (!nativeDesc?.set) return;

    Object.defineProperty(HTMLMediaElement.prototype, "srcObject", {
      get: nativeDesc.get,
      set(stream) {
        if (stream instanceof MediaStream) {
          stream.getAudioTracks().forEach(onAudioTrack);
        }
        nativeDesc.set.call(this, stream);
      },
      configurable: true,
      enumerable: true,
    });
  }

  function collectTracksFromExistingConnections() {
    for (const pc of interceptedConnections) {
      try {
        for (const r of pc.getReceivers()) {
          if (r.track) onRemoteAudioTrack(r.track);
        }
      } catch {}
    }
  }

  function getLiveAudioTracks() {
    return audioTracks.filter((t) => t.readyState === "live");
  }

  // ═══════════════════════════════════════════════════════════════════════
  // Layer 2 — Cross-Origin Loopback (sender side)
  // ═══════════════════════════════════════════════════════════════════════

  async function createLoopbackOffer(tracks) {
    const pc = new NativeRTCPeerConnection({ iceServers: [] });
    tracks.forEach((t) => pc.addTrack(t));

    await pc.setLocalDescription(await pc.createOffer());
    await waitForIceGathering(pc);

    return { pc, offerSDP: pc.localDescription.toJSON() };
  }

  function sendOfferToMainPage(offerSDP) {
    window.parent.postMessage({ type: "webrtc-bridge-offer", sdp: offerSDP }, "*");
  }

  function waitForAnswerFromMainPage(loopbackPC) {
    return new Promise((resolve) => {
      function onMessage(event) {
        if (event.data?.type !== "webrtc-bridge-answer") return;
        window.removeEventListener("message", onMessage);
        loopbackPC
          .setRemoteDescription(new RTCSessionDescription(event.data.sdp))
          .then(() => resolve(true))
          .catch((err) => {
            console.error("[webrtcBridge] Failed to complete loopback:", err);
            resolve(false);
          });
      }
      window.addEventListener("message", onMessage);
      setTimeout(() => resolve(false), 10_000);
    });
  }

  // ═══════════════════════════════════════════════════════════════════════
  // Entry point
  // ═══════════════════════════════════════════════════════════════════════

  interceptPeerConnections(onRemoteAudioTrack);
  interceptSrcObjectSetter(onRemoteAudioTrack);

  window.__startBridgeLoopback = async function bridgeAudioToMainPage() {
    collectTracksFromExistingConnections();

    const liveTracks = getLiveAudioTracks();
    if (liveTracks.length === 0) {
      console.warn("[webrtcBridge] No live audio tracks to bridge");
      return false;
    }

    const { pc, offerSDP } = await createLoopbackOffer(liveTracks);
    sendOfferToMainPage(offerSDP);
    return waitForAnswerFromMainPage(pc);
  };

  function waitForIceGathering(pc) {
    if (pc.iceGatheringState === "complete") return Promise.resolve();
    return new Promise((resolve) => {
      pc.addEventListener("icegatheringstatechange", () => {
        if (pc.iceGatheringState === "complete") resolve();
      });
    });
  }
})();
