type ActiveUpload = { abort: () => void };

const activeUploads = new Map<number, ActiveUpload>();
let nextImportId = 0;

export function useUploadStatus() {
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

  return { registerUpload, unregisterUpload, abortActiveUploads };
}
