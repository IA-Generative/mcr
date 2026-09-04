const BEEP_FREQUENCY_HZ = 880;
const BEEP_DURATION_S = 0.12;
const BEEP_GAP_S = 0.08;
const BEEP_PEAK_GAIN = 0.15;
const BEEP_RAMP_S = 0.01;
const BEEPS_PER_ALERT = 2;

let alertContext: AudioContext | undefined;

function getAlertContext(): AudioContext | undefined {
  if (alertContext) return alertContext;

  const AudioContextConstructor =
    window.AudioContext ??
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AudioContextConstructor) return undefined;

  alertContext = new AudioContextConstructor();
  return alertContext;
}

function scheduleBeep(context: AudioContext, startAt: number): void {
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  oscillator.frequency.value = BEEP_FREQUENCY_HZ;

  gain.gain.setValueAtTime(0, startAt);
  gain.gain.linearRampToValueAtTime(BEEP_PEAK_GAIN, startAt + BEEP_RAMP_S);
  gain.gain.setValueAtTime(BEEP_PEAK_GAIN, startAt + BEEP_DURATION_S - BEEP_RAMP_S);
  gain.gain.linearRampToValueAtTime(0, startAt + BEEP_DURATION_S);

  oscillator.connect(gain);
  // IMPORTANT: the speakers only — connecting this to the recorder's destination node would inject beeps into every report.
  gain.connect(context.destination);

  oscillator.start(startAt);
  oscillator.stop(startAt + BEEP_DURATION_S);
}

export function playNoSignalAlert(): void {
  try {
    const context = getAlertContext();
    if (!context) return;
    if (context.state === 'suspended') void context.resume();

    for (let beepIndex = 0; beepIndex < BEEPS_PER_ALERT; beepIndex += 1) {
      scheduleBeep(context, context.currentTime + beepIndex * (BEEP_DURATION_S + BEEP_GAP_S));
    }
  } catch {
    /* a beep that fails must never break the recording it is warning about */
  }
}

export function closeAlertAudio(): void {
  try {
    void alertContext?.close();
  } catch {
    /* the context is being dropped anyway */
  } finally {
    alertContext = undefined;
  }
}
