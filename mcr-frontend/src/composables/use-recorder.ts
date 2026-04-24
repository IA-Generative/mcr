import { useStopwatch } from 'vue-timer-hook';

const currentAudioId = ref<string | undefined>('');
const mediaRecorder = ref<MediaRecorder | undefined>(undefined);
const TIME_BETWEEN_CHUNK_SPLIT = 60_000; // 1 minute

const stopwatchSettings = {
  offsetTimestamp: 0,
  autoStart: false,
};

const stopwatch = useStopwatch(stopwatchSettings.offsetTimestamp, stopwatchSettings.autoStart);

type MediaRecorderState = 'inactive' | 'recording' | 'paused';
const recorderState = ref<MediaRecorderState>('inactive');

const isRecording = computed(() => {
  return recorderState.value === 'recording';
});

export const isInactive = computed(() => {
  return recorderState.value === 'inactive';
});

async function getUserPermission() {
  if (!navigator.mediaDevices) return false;
  try {
    await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (error) {
    console.error('Error requesting audio permission:', error);
  }
}

function _preventSendingAudio() {
  if (!mediaRecorder.value) return;
  mediaRecorder.value.ondataavailable = null;
  mediaRecorder.value.onstop = null;
}

function _initMediaRecorderEvents(options: RecordingOptions) {
  if (!mediaRecorder.value) return;

  mediaRecorder.value.onstart = () => {
    recorderState.value = 'recording';
  };

  mediaRecorder.value.onresume = () => {
    recorderState.value = 'recording';
  };

  mediaRecorder.value.onpause = () => {
    recorderState.value = 'paused';
  };

  mediaRecorder.value.onstop = () => {
    recorderState.value = 'inactive';
    options.onStopEventHandler?.();
  };

  mediaRecorder.value.ondataavailable =
    options.onDataAvailableHandler != undefined ? options.onDataAvailableHandler : null;
}

export type RecordingStartContext = {
  stream: MediaStream;
  recorder: MediaRecorder;
};

type RecordingOptions = {
  onDataAvailableHandler?: (event: BlobEvent) => void;
  onStopEventHandler?: () => void;
  onRecordingStart?: (ctx: RecordingStartContext) => void;
  numberOfChunkAlreadyRecorded?: number;
};

function initializeStopwatchWithOffset(numberOfChunkAlreadyRecorded?: number): void {
  let offsetTimestamp = stopwatchSettings.offsetTimestamp;
  if (numberOfChunkAlreadyRecorded != null && numberOfChunkAlreadyRecorded != undefined) {
    offsetTimestamp = calculateElapsedSecondsFromChunkNumber(numberOfChunkAlreadyRecorded);
  }
  stopwatch.reset(offsetTimestamp, false);
}

function setAudioDeviceId(id: string) {
  currentAudioId.value = id;
}

async function startRecording(options: RecordingOptions = {}) {
  if (!currentAudioId.value) {
    const devices = await getAudioInputDevices();
    currentAudioId.value = getDefaultDeviceId(devices);
  }

  const mediaStream = await navigator.mediaDevices.getUserMedia({
    audio: { deviceId: { exact: currentAudioId.value } },
  });

  mediaRecorder.value = new MediaRecorder(mediaStream, {
    mimeType: 'audio/webm',
  });
  _initMediaRecorderEvents(options);
  mediaRecorder.value.start(TIME_BETWEEN_CHUNK_SPLIT);
  initializeStopwatchWithOffset(options.numberOfChunkAlreadyRecorded);
  stopwatch.start();

  options.onRecordingStart?.({ stream: mediaStream, recorder: mediaRecorder.value });
}

async function getAudioInputDevices() {
  await getUserPermission();
  const devices = await navigator.mediaDevices.enumerateDevices();

  return devices.filter((device) => device.kind === 'audioinput');
}

function getDefaultDeviceId(devices: MediaDeviceInfo[]): string {
  if (devices.length === 0) {
    return '';
  }
  const chromiumDefaultDeviceId = 'default';
  const firefoxDefaultDeviceId = devices[0].deviceId;

  const foundChromiumDefault = devices.some((d) => d.deviceId === chromiumDefaultDeviceId);
  if (foundChromiumDefault) {
    return chromiumDefaultDeviceId;
  } else {
    return firefoxDefaultDeviceId;
  }
}

function resumeRecording() {
  if (!mediaRecorder.value || mediaRecorder.value.state === 'inactive') return;

  mediaRecorder.value.resume();
  stopwatch.start();
}

function stopRecording() {
  if (!mediaRecorder.value || mediaRecorder.value.state === 'inactive') return;

  mediaRecorder.value.stop();
  stopwatch.reset(stopwatchSettings.offsetTimestamp, stopwatchSettings.autoStart);

  releaseAudioResources();
}

function releaseAudioResources() {
  if (!mediaRecorder.value) return;

  mediaRecorder.value.stream.getTracks().forEach((track) => track.stop());
  mediaRecorder.value = undefined;
}

function abortRecording() {
  if (!mediaRecorder.value || mediaRecorder.value.state === 'inactive') return;

  _preventSendingAudio();
  stopRecording();
  // We set the state to inactive immediately because when deleting the meeting, we don't want to wait for the stop event.
  // This is important to allow the user to navigate away from the page without confirmation.
  recorderState.value = 'inactive';
}

function pauseRecording() {
  if (!mediaRecorder.value || mediaRecorder.value.state === 'inactive') return;

  mediaRecorder.value.pause();
  stopwatch.pause();
}

export function calculateElapsedSecondsFromChunkNumber(chunkCount: number): number {
  const timePerChunkInSeconds = TIME_BETWEEN_CHUNK_SPLIT / 1000;
  return chunkCount * timePerChunkInSeconds;
}

export function useRecorder() {
  return {
    isRecording,
    isInactive,
    time: {
      seconds: stopwatch.seconds,
      minutes: stopwatch.minutes,
      hours: stopwatch.hours,
    },
    getAudioInputDevices,
    getDefaultDeviceId,
    setAudioDeviceId,
    startRecording,
    resumeRecording,
    abortRecording,
    stopRecording,
    pauseRecording,
  };
}
