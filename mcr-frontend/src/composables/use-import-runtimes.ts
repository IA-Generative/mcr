export type ItemRuntime = {
  file: File;
  controller: AbortController;
  stopTranscoding?: () => void;
  registryId: number;
};

const runtimes = new Map<number, ItemRuntime>();
const startedUploads = new Set<number>();
const startedTranscodes = new Set<number>();

export function useImportRuntimes() {
  function forgetStarted(id: number): void {
    startedTranscodes.delete(id);
    startedUploads.delete(id);
  }

  function forget(id: number): void {
    runtimes.delete(id);
    forgetStarted(id);
  }

  function forgetAll(): void {
    // A retryable failure keeps its runtime, hence its File, so the user can try
    // again. Discarding the batch is what tells us nobody will: without this the
    // files stay in memory until the page reloads.
    runtimes.clear();
    startedUploads.clear();
    startedTranscodes.clear();
  }

  return { runtimes, startedUploads, startedTranscodes, forget, forgetStarted, forgetAll };
}
