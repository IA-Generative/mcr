;(function () {
  window.__mainReceiverReady = false;

  // ═══════════════════════════════════════════════════════════════════════
  // Layer 2 — Cross-Origin Loopback (receiver side)
  // ═══════════════════════════════════════════════════════════════════════

  function sendAnswerToIframe(source, answerSDP) {
    source.postMessage({ type: "webrtc-bridge-answer", sdp: answerSDP }, "*");
  }

  function attachAudioTrackToDOM(track, streams) {
    const stream = streams?.[0] || new MediaStream([track]);
    const audioEl = document.createElement("audio");
    audioEl.srcObject = stream;
    audioEl.style.display = "none";
    audioEl.setAttribute("data-main-receiver", "true");
    document.body.appendChild(audioEl);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // Entry point
  // ═══════════════════════════════════════════════════════════════════════

  function createReceiverPC() {
    const pc = new RTCPeerConnection({ iceServers: [] });
    // Register track listener BEFORE setRemoteDescription — the track event
    // fires during setRemoteDescription and would be missed otherwise.
    pc.addEventListener("track", (e) => {
      if (e.track.kind === "audio") attachAudioTrackToDOM(e.track, e.streams);
    });
    return pc;
  }

  async function acceptLoopbackOffer(pc, offerSDP) {
    await pc.setRemoteDescription(new RTCSessionDescription(offerSDP));
    await pc.setLocalDescription(await pc.createAnswer());
    await waitForIceGathering(pc);
    return pc.localDescription.toJSON();
  }

  window.addEventListener("message", async function handleBridgeOffer(event) {
    if (event.data?.type !== "webrtc-bridge-offer") return;

    try {
      const pc = createReceiverPC();
      const answerSDP = await acceptLoopbackOffer(pc, event.data.sdp);
      sendAnswerToIframe(event.source, answerSDP);
      window.__mainReceiverReady = true;
    } catch (err) {
      console.error("[mainReceiver] Error:", err);
    }
  });

  function waitForIceGathering(pc) {
    if (pc.iceGatheringState === "complete") return Promise.resolve();
    return new Promise((resolve) => {
      pc.addEventListener("icegatheringstatechange", () => {
        if (pc.iceGatheringState === "complete") resolve();
      });
    });
  }
})();
