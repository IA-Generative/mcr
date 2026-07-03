type ActiveUpload = { abort: () => void };

/**
 * Minimal shared source for the navigation net (#885), keyed by a synthetic import id
 * (no meeting exists yet during the transcode phase). #893 should build its own richer
 * per-file store rather than extend this one; the only contract to preserve is
 * `hasActiveUploads`.
 */
const activeUploads = reactive(new Map<number, ActiveUpload>());
let nextImportId = 0;

export function useUploadStatus() {
  const hasActiveUploads = computed(() => activeUploads.size > 0);

  function registerUpload(upload: ActiveUpload): number {
    const id = ++nextImportId;
    activeUploads.set(id, upload);
    return id;
  }

  function unregisterUpload(id: number): void {
    activeUploads.delete(id);
  }

  function abortActiveUploads(): void {
    // unregister before aborting: the import's own finally may only run after the
    // upload mutation exhausts its retry delays, and the guard must not re-prompt
    // for an import that is already being torn down
    activeUploads.forEach((upload, id) => {
      activeUploads.delete(id);
      upload.abort();
    });
  }

  return { hasActiveUploads, registerUpload, unregisterUpload, abortActiveUploads };
}
