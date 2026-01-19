import { FFmpeg } from '@ffmpeg/ffmpeg';
import { fetchFile, toBlobURL } from '@ffmpeg/util';

const baseURL = 'https://cdn.jsdelivr.net/npm/@ffmpeg/core-mt@0.12.10/dist/esm';
const ERROR_TERMINATED = 'called FFmpeg.terminate()';

export function useVideo2audioConverter(
  onProgressCallback?: (progress: number, time: number) => void,
) {
  const ffmpeg = new FFmpeg();
  const isLoading = ref(false);

  let scripts = {
    core: '',
    wasm: '',
    worker: '',
  };

  async function loadScripts() {
    /** As per this github issue: https://github.com/ffmpegwasm/ffmpeg.wasm/issues/719
     * It is not possible to use signals to abort the execution of the ffmpeg process.
     * The only way to stop the ffmpeg process is to terminate the worker.
     * For this reason, we ensure that the scripts are loaded only once by using a component ref areScriptLoaded.
     * And we also use the ffmpeg.loaded property to check if the ffmpeg instance is already initialize.
     */

    if (areScriptsLoaded()) return;

    scripts = {
      // JS file that contains the binding to allow js to invoke the WASM and functions inside of it
      // Can be thought of an index.js of a module
      core: await toBlobURL(`${baseURL}/ffmpeg-core.js`, 'text/javascript'),

      // Compiled binary that contains the ffmpeg functions
      wasm: await toBlobURL(`${baseURL}/ffmpeg-core.wasm`, 'application/wasm'),

      // Worker that runs the ffmpeg functions in a separate thread
      worker: await toBlobURL(`${baseURL}/ffmpeg-core.worker.js`, 'text/javascript'),
    };
  }

  function areScriptsLoaded() {
    return scripts.core !== '' && scripts.wasm !== '' && scripts.worker !== '';
  }

  async function loadFFmpeg() {
    if (ffmpeg.loaded) {
      return;
    }
    ffmpeg.on('progress', ({ progress, time }) => onProgressCallback?.(progress, time));

    await ffmpeg.load({
      coreURL: scripts.core,
      wasmURL: scripts.wasm,
      workerURL: scripts.worker,
    });
  }

  /**
   * The transcode function turns a video file into an mp3 audio file.
   * @param {File} file - The video file to convert.
   * @returns {File} The audio file created as an mp3 with the name oldFileName.mp3.
   */
  async function transcodeToMp3(file: File) {
    const fileData = await fetchFile(file);
    const fileName = file.name;
    isLoading.value = true;
    await loadScripts();
    await loadFFmpeg();
    isLoading.value = false;

    const fileNameDotMp3 = `${fileName.split('.').slice(0, -1).join('.')}.mp3`;
    // write the file to the ffmpeg virtual file system (VFS)

    try {
      await ffmpeg.writeFile(fileName, fileData);
      // run the ffmpeg command to convert the video to mp3 and create the output.mp3 file in the ffmpeg VFS
      await ffmpeg.exec(['-i', fileName, 'output.mp3']);
      // read the output.mp3 file from the ffmpeg VFS
      const data = await ffmpeg.readFile('output.mp3');

      const blob = new Blob([(data as Uint8Array).buffer], { type: 'audio/mpeg' });
      return new File([blob], fileNameDotMp3, { type: 'audio/mpeg' });
    } catch (error) {
      if (error instanceof Error && error.message !== ERROR_TERMINATED) {
        console.error(`Transcoding failed: ${error}`);
      }
      throw new Error(`Transcoding failed: ${error}`);
    }
  }

  function stopTranscoding() {
    ffmpeg.terminate();
  }

  return {
    transcodeToMp3,
    stopTranscoding,
    isLoading,
  };
}
