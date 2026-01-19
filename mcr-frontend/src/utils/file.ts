import type { AxiosResponse } from 'axios';

export function downloadFileFromAxios(response: AxiosResponse, filename = 'downloaded_document') {
  const url = window.URL.createObjectURL(
    new Blob([response.data], { type: response.headers['content-type'] }),
  );

  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

export function getFileExtension(file: File): string | undefined {
  const parts = file.name.split('.');
  return parts.length > 1 ? parts.pop() : undefined;
}
