;(function initStreamUtils() {
  // MixedAudioGraph gets audio from all media elements on the page
  // and mixes them into a single MediaStream.
  // If no real sources are present, it injects a silent source.
  class MixedAudioGraph {
    constructor() {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      this.mediaStreamDestination = this.audioContext.createMediaStreamDestination();
      this.sources = new Map();
      this.silence = null;
      this.mutationObserver = null;

      // Attach media elements already in the DOM
      this._scanAndAttachAll();
      // Watching the DOM for media elements being added/removed
      this._startObserver();
      // Ensure downstream always has an audio track (silence until real audio exists)
      this._updateSilenceNode();
    }

    get stream() {
      return this.mediaStreamDestination.stream;
    }

    dispose() {
      // Stop observers, disconnect nodes, and close context
      try { this.mutationObserver && this.mutationObserver.disconnect(); } catch {}
      this.mutationObserver = null;

      this.sources.forEach((node) => { try { node.disconnect(); } catch {} });
      this.sources.clear();

      this._stopSilence();

      try { this.mediaStreamDestination.disconnect?.(); } catch {}
      try { this.audioContext.close(); } catch {}
    }

    _addElement(mediaElement) {
      // Ignore nulls and avoid adding the same element twice
      let hasMediaElement = !mediaElement || this.sources.has(mediaElement);
      if (hasMediaElement) return;

      // Only attach if the element has a real MediaStream with at least one audio track
      const mediaStream = mediaElement.srcObject instanceof MediaStream ? mediaElement.srcObject : null;
      if (!mediaStream) return;
      if (mediaStream.getAudioTracks().length === 0) return;

      // Convert the element's MediaStream into a Web Audio source and route to the mix
      const sourceNode = new MediaStreamAudioSourceNode(this.audioContext, { mediaStream });
      sourceNode.connect(this.mediaStreamDestination);
      this.sources.set(mediaElement, sourceNode);
    }

    _removeElement(mediaElement) {
      const sourceNode = this.sources.get(mediaElement);
      if (!sourceNode) return;
      try { sourceNode.disconnect(); } catch {}
      this.sources.delete(mediaElement);
    }

    _scanAndAttachAll() {
      // Pick up the media elements already present before the observer runs
      document.querySelectorAll("audio,video").forEach((mediaElement) => this._addElement(mediaElement));
    }

    _startObserver() {
      // Watch DOM changes so we can react to media elements added/removed
      this.mutationObserver = new MutationObserver((mutations) => {
        let changed = false;

        mutations.forEach((mutation) => {
          mutation.addedNodes?.forEach((domNode) => {
            if (!isHtmlElement(domNode)) return;
            if (isMediaElement(domNode)) {
              this._addElement(domNode); changed = true; }
            domNode.querySelectorAll?.("audio,video").forEach((mediaElement) => {
               this._addElement(mediaElement); changed = true;
              });
          });

          mutation.removedNodes?.forEach((domNode) => {
            if (!isHtmlElement(domNode)) return;
            if (isMediaElement(domNode)) {
              this._removeElement(domNode); changed = true;
            }
            domNode.querySelectorAll?.("audio,video").forEach((mediaElement) => {
              this._removeElement(mediaElement); changed = true;
            });
          });
        });

        // If the set of sources changed, check if we need silence
        if (changed) this._updateSilenceNode();
      });

      this.mutationObserver.observe(document.documentElement, { childList: true, subtree: true });
    }

    _updateSilenceNode() {
      // Silence until a real source exists
      if (this.sources.size === 0) {
        this._ensureSilence();
      } else {
        this._stopSilence();
      }
    }

    _ensureSilence() {
      if (this.silence) return;
      const gain = this.audioContext.createGain();
      gain.gain.value = 0;

      const constantSourceNode = this.audioContext.createConstantSource();
      constantSourceNode.offset.value = 0;
      constantSourceNode.connect(gain).connect(this.mediaStreamDestination);
      constantSourceNode.start();

      this.silence = constantSourceNode;
    }

    _stopSilence() {
      if (!this.silence) return;
      try { this.silence.stop(); } catch {}
      try { this.silence.disconnect(); } catch {}
      this.silence = null;
    }
  }

  function createMixedAudioStream() {
    const graph = new MixedAudioGraph();
    return { stream: graph.stream, graph };
  }

  function disposeMixedAudioGraph(graph) {
    try { graph?.dispose(); } catch {}
  }

  function isHtmlElement(node) {
    return node instanceof HTMLElement;
  }

  function isMediaElement(node) {
    return node.matches?.("audio,video");
  }

  window.StreamUtils = {
    createMixedAudioStream,
    disposeMixedAudioGraph,
  };
})();
