import { t, te, type MessageKeys } from '@/plugins/i18n';
import type { DeliverableFeedbackGroup } from '@/services/deliverable-feedback/deliverable-feedback.types';

const ROOT = 'meeting-v2.deliverable-feedback.reasons';

export function reasonLabel(group: DeliverableFeedbackGroup, reason: string): string {
  const scoped = `${ROOT}.${group}.${reason}` as MessageKeys;
  if (te(scoped)) return t(scoped);

  const shared = `${ROOT}.shared.${reason}` as MessageKeys;
  if (te(shared)) return t(shared);

  return reason;
}
