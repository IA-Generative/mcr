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

export const AUDIO_IMPORT_EXTENSIONS: readonly string[] = [
  'aac',
  'flac',
  'm4a',
  'mp3',
  'ogg',
  'opus',
  'wav',
];
export const VIDEO_IMPORT_EXTENSIONS: readonly string[] = ['mkv', 'mov', 'mp4', 'webm'];
export const ALLOWED_IMPORT_EXTENSIONS: readonly string[] = [
  ...AUDIO_IMPORT_EXTENSIONS,
  ...VIDEO_IMPORT_EXTENSIONS,
].sort();
export const IMPORT_ACCEPT_ATTR = ALLOWED_IMPORT_EXTENSIONS.map((e) => `.${e}`).join(',');
export const ALLOWED_IMPORT_FORMATS_LABEL = ALLOWED_IMPORT_EXTENSIONS.map((e) => `.${e}`).join(
  ', ',
);

export function extractFilenameFromResponse(response: AxiosResponse): string | undefined {
  // mcr-core always emits Content-Disposition as filename*=UTF-8''<url-encoded>
  const header = response.headers['content-disposition'];
  if (typeof header !== 'string') return undefined;
  const match = header.match(/filename\*=UTF-8''([^;]+)/i);
  return match ? decodeURIComponent(match[1]) : undefined;
}
