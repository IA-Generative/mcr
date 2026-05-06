import {
  getNumberOfDaysBeforeMeetingDeletion,
  meetingDateIsInAlertPeriod,
} from '@/services/meetings/meetings-datetime';
import type { DsfrAlertType } from '@gouvminint/vue-dsfr';
import type { MaybeRefOrGetter } from 'vue';

export function useMeetingPeremption(creationDate: MaybeRefOrGetter<string | undefined>) {
  const daysBeforeDeletion = computed(() => {
    const date = toValue(creationDate);
    if (!date) return undefined;
    const days = getNumberOfDaysBeforeMeetingDeletion(date);
    return days > 0 ? days : undefined;
  });

  const isInAlertPeriod = computed(() => {
    const date = toValue(creationDate);
    if (!date) return false;
    return meetingDateIsInAlertPeriod(date);
  });

  const alertType = computed<DsfrAlertType>(() => (isInAlertPeriod.value ? 'warning' : 'info'));

  return { daysBeforeDeletion, isInAlertPeriod, alertType };
}
