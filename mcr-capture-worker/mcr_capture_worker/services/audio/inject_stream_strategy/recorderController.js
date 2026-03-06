;(function initRecorderController() {
  class MeetingAudioRecorderController {
    constructor() {
      this.mediaRecorder = undefined;
      this.streamMonitorIntervalId = undefined;
      this.currentStreamId = null;
      this.hasSentStartEvent = false;
      this.isStopping = false;
      this.mixedGraph = null;
    }

    async start() {
      // Create a stable mixed stream (id doesn't change when participants change)
      const { stream, graph } = window.StreamUtils.createMixedAudioStream();
      this.mixedGraph = graph;

      try { await this.mixedGraph.ac.resume?.(); } catch {}

      this.createAndStartMediaRecorder(stream);

      const intervalMs = window.AudioConfig?.STREAM_CHECK_INTERVAL_MS ?? 2000;
      this.streamMonitorIntervalId = setInterval(() => {
        if (this.isStopping) return;
        // Silence if no source; otherwise stop the silence
        if (this.mixedGraph?.sources?.size === 0) {
          this.mixedGraph?._ensureSilence?.();
        } else {
          this.mixedGraph?._stopSilence?.();
        }
      }, intervalMs);
    }

    stop() {
      this.isStopping = true;

      if (this.streamMonitorIntervalId) {
        clearInterval(this.streamMonitorIntervalId);
        this.streamMonitorIntervalId = undefined;
      }

      const isRecording = this.mediaRecorder && this.mediaRecorder.state === "recording";
      if (isRecording) {
        this.mediaRecorder.stop();
        console.log("Audio capture stopped.");
      } else {
        console.warn("No active recording to stop.");
      }

      window.StreamUtils.disposeMixedAudioGraph(this.mixedGraph);
      this.mixedGraph = null;

      this.currentStreamId = null;
      this.hasSentStartEvent = false;
    }

    canAcquire() {
      return true;
    }

    createAndStartMediaRecorder(stream) {
      this.currentStreamId = stream.id;
      console.log("Starting MediaRecorder with mixed stream:", stream.id);

      const options = { mimeType: window.AudioConfig.RECORDER_MIME_TYPE };

      try {
        this.mediaRecorder = new MediaRecorder(stream, options);
      } catch (e) {
        console.error("Failed to create MediaRecorder with mimeType:", options.mimeType, e);
        this.mediaRecorder = new MediaRecorder(stream);
      }

      this.mediaRecorder.ondataavailable = async (event) => {
        if (event.data?.size > 0) {
          try {
            const arrayBuffer = await event.data.arrayBuffer();
            const uint8Array = new Uint8Array(arrayBuffer);
            await window.sendOnDataavailableToWorker({ js_bytes: uint8Array });
          } catch (error) {
            console.error("Error sending audio data to worker:", error);
          }
        }
      };

      this.mediaRecorder.onstart = async () => {
        if (!this.hasSentStartEvent) {
          await window.sendOnStartToWorker();
          this.hasSentStartEvent = true;
        }
      };

      this.mediaRecorder.onstop = async () => {
        if (!this.streamMonitorIntervalId) {
          await window.sendOnStopToWorker();
        }
      };

      this.mediaRecorder.onerror = (event) => {
        console.error("MediaRecorder error: ", event.error || event);
      };

      this.mediaRecorder.start(window.AudioConfig.CHUNK_DURATION_MS);
    }
  }

  window.MeetingAudioRecorderController = MeetingAudioRecorderController;
})();
