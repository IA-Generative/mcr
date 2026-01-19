;(function exposeAPI() {
  const controller = new window.MeetingAudioRecorderController();

  window.startRecording = () => controller.start();
  window.stopRecording = () => controller.stop();
  window.canAcquireAudioStream = () => controller.canAcquire();
})();


