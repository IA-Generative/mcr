// Global Variables
window.mediaRecorder = undefined;
const chunkDuration = 10000; // 10 seconds

function startRecording() {
  const audioStream = getAudioStreamFromAudioOrVideoElement();

  if (!(audioStream instanceof MediaStream)) {
    console.error(
      "getAudioStreamRTC() did not return a MediaStream:",
      audioStream
    );
    return;
  }

  window.mediaRecorder = new MediaRecorder(audioStream, {
    mimeType: "audio/webm; codecs=opus",
  });

  window.mediaRecorder.start(chunkDuration);

  window.mediaRecorder.ondataavailable = async (event) => {
    if (event.data.size > 0) {
      try {
        const arrayBuffer = await event.data.arrayBuffer();
        const uint8Array = new Uint8Array(arrayBuffer);
        const object = { js_bytes: uint8Array };

        await window.sendOnDataavailableToWorker(object);
      } catch (error) {
        console.error("Error sending audio data to worker:", error);
      }
    }
  };

  window.mediaRecorder.onstart = async () => {
    await window.sendOnStartToWorker();
  };

  window.mediaRecorder.onstop = async () => {
    await window.sendOnStopToWorker();
  };

  window.mediaRecorder.onerror = function (event) {
    console.error("MediaRecorder error: ", event.error);
  };
}

function stopRecording() {
  if (window.mediaRecorder && window.mediaRecorder.state === "recording") {
    window.mediaRecorder.stop();
    console.log("Audio capture stopped.");
  } else {
    console.warn("No active recording to stop.");
  }
}

function getStreamFromAudioElement() {
  const audioEl = document.querySelector("audio");
  if (audioEl?.srcObject instanceof MediaStream) {
    console.log("Using audio element's MediaStream:", audioEl.srcObject);
    return audioEl.srcObject;
  }
  return null;
}

function getStreamFromVideoElement() {
  const videoEl = document.querySelector("video");
  if (videoEl?.srcObject instanceof MediaStream) {
    const audioTracks = videoEl.srcObject.getAudioTracks();
    if (audioTracks.length > 0) {
      const audioStream = new MediaStream(audioTracks);
      console.log("Extracted audio tracks from video element:", audioStream);
      return audioStream;
    }
  }
  return null;
}

function getAudioStreamFromAudioOrVideoElement() {
  const audioStream = getStreamFromAudioElement();
  if (audioStream) return audioStream;

  const videoStream = getStreamFromVideoElement();
  if (videoStream) return videoStream;

  console.error("No usable MediaStream found in audio or video elements.");
  return null;
}

function canAcquireAudioStream() {
  const audioStream = getAudioStreamFromAudioOrVideoElement();
  return audioStream instanceof MediaStream;
}

window.startRecording = startRecording;
window.stopRecording = stopRecording;
window.canAcquireAudioStream = canAcquireAudioStream;