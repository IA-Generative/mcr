import { describe, it, expect } from 'vitest';
import type { AxiosResponse } from 'axios';
import { extractFilenameFromResponse } from './file';

function buildResponse(headers: Record<string, string>): AxiosResponse {
  return { headers } as unknown as AxiosResponse;
}

describe('extractFilenameFromResponse', () => {
  it('decodes the UTF-8 percent-encoded form', () => {
    const response = buildResponse({
      'content-disposition': "attachment; filename*=UTF-8''Releve_Decision_R%C3%A9union.docx",
    });
    expect(extractFilenameFromResponse(response)).toBe('Releve_Decision_Réunion.docx');
  });

  it('returns undefined when the header is missing', () => {
    const response = buildResponse({ 'content-type': 'application/docx' });
    expect(extractFilenameFromResponse(response)).toBeUndefined();
  });
});
