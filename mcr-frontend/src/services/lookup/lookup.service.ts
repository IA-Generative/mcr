import { t } from '@/plugins/i18n';
import HttpService, { API_PATHS } from '../http/http.service';
import type { LookupDto, LookupResponseDto } from './lookup.types';
// import { useI18n } from 'vue-i18n';

export async function lookupComu(comuMeeting: LookupDto): Promise<LookupResponseDto> {
  const { data } = await HttpService.post(API_PATHS.LOOKUP, comuMeeting);
  return data;
}

export function parseComuUrl(url: string): LookupDto {
  if (!url) {
    throw new Error('Invalid URL');
  }

  const comuUrl = new URL(url);

  const comu_meeting_id = comuUrl.pathname.split('/').pop();
  const secret = comuUrl.searchParams.get('secret');

  if (!comu_meeting_id || !secret) {
    throw new Error(t('meeting.form.errors.url.invalid-comu-parsing'));
  }

  return { comu_meeting_id, secret };
}
