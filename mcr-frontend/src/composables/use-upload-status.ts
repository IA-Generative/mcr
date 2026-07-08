type ActiveUpload = { abort: () => void };

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
    activeUploads.forEach((upload, id) => {
      activeUploads.delete(id);
      upload.abort();
    });
  }

  return { hasActiveUploads, registerUpload, unregisterUpload, abortActiveUploads };
}
