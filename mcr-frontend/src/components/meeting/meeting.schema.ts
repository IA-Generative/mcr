import { computed } from 'vue';
import yup from '@/config/yup';
import {
  OnlineMeetingPlatforms,
  type AddOnlineMeetingDto,
} from '@/services/meetings/meetings.types';
import { t } from '@/plugins/i18n';
import type { Nullable } from '@/utils/types';
import { useFeatureFlag } from '@/composables/use-feature-flag';

const comuDomainPattern = [
  /webconf\.comu\.gouv\.fr/,
  /webconf\.comu\.interieur\.rie\.gouv\.fr/,
  /webconf\.comu\.minint\.fr/,
]
  .map((r) => r.source)
  .join('|');

const comuUrlPattern = {
  secret: /\?secret=[A-Za-z0-9_.]{22}/,
  meetingId: /\d+/,
  maybeLanguageCode: /(\/[a-z]{2}-[A-Z]{2})?/,
};

export const comuPrivateUrlValidator = RegExp(
  `^https://(${comuDomainPattern})${comuUrlPattern.maybeLanguageCode.source}/meeting/${comuUrlPattern.meetingId.source}${comuUrlPattern.secret.source}$`,
);

export const comuPublicUrlValidator = RegExp(
  `^https://(${comuDomainPattern})${comuUrlPattern.maybeLanguageCode.source}/meeting/${comuUrlPattern.meetingId.source}$`,
);

const webinaireUrlPattern = {
  domain: /webinaire\.numerique\.gouv\.fr/,
  meetingId: /\d+/,
  creatorId: /\d+/,
  validationHash: /[a-f0-9]{40}/,
};

export const webinaireModeratorUrlValidator = RegExp(
  `^https://${webinaireUrlPattern.domain.source}/meeting/signin/moderateur/${webinaireUrlPattern.meetingId.source}/creator/${webinaireUrlPattern.creatorId.source}/hash/${webinaireUrlPattern.validationHash.source}$`,
);

export const webinairePublicUrlValidator = RegExp(`^https://${webinaireUrlPattern.domain.source}`);

const webconfUrlPattern = {
  domain: /webconf\.numerique\.gouv\.fr/,
  meetingName: /(?=(?:.*\d){3,})[A-Za-z0-9]{10,}/,
};

export const webconfUrlValidator = RegExp(
  `^https://${webconfUrlPattern.domain.source}/${webconfUrlPattern.meetingName.source}$`,
);

const visioUrlPattern = {
  domain: /visio\.numerique\.gouv\.fr/,
  meetingSlug: /[a-z]{3}-[a-z]{4}-[a-z]{3}/,
};

export const visioUrlValidator = RegExp(
  `^https://${visioUrlPattern.domain.source}/${visioUrlPattern.meetingSlug.source}$`,
);

export const visioIncompleteUrlValidator = RegExp(`${visioUrlPattern.domain.source}`);

type PlatformUrlConfig = {
  name: OnlineMeetingPlatforms;
  validator: RegExp;
  errorValidator?: RegExp;
  errorMessage?: string;
};

const isVisioEnabled = useFeatureFlag('visio');

const platformConfigs = computed<PlatformUrlConfig[]>(() => {
  const configs: PlatformUrlConfig[] = [
    {
      name: 'COMU',
      validator: comuPrivateUrlValidator,
      errorValidator: comuPublicUrlValidator,
      errorMessage: t('meeting.form.errors.url.not-private'),
    },
    {
      name: 'WEBINAIRE',
      validator: webinaireModeratorUrlValidator,
      errorValidator: webinairePublicUrlValidator,
      errorMessage: t('meeting.form.errors.url.not-moderator'),
    },
    {
      name: 'WEBCONF',
      validator: webconfUrlValidator,
    },
  ];

  if (isVisioEnabled.value) {
    configs.push({
      name: 'VISIO',
      validator: visioUrlValidator,
      errorValidator: visioIncompleteUrlValidator,
      errorMessage: t('meeting.form.errors.url.invalid-visio-url'),
    });
  }

  return configs;
});

const notSupportedErrorMessage = computed(() =>
  isVisioEnabled.value
    ? t('meeting.form.errors.url.not-supported.visio-enabled')
    : t('meeting.form.errors.url.not-supported.visio-disabled'),
);

function validateUrl(url: string | null) {
  if (!url) return true;
  return platformConfigs.value.some(({ validator }) => validator.test(url));
}

function selectErrorMessage(url: string | null) {
  if (url !== null) {
    const match = platformConfigs.value.find(({ errorValidator }) => errorValidator?.test(url));
    if (match?.errorMessage) return match.errorMessage;
  }
  return notSupportedErrorMessage.value;
}

type AddOnlineMeetingFields = Omit<AddOnlineMeetingDto, 'name_platform' | 'creation_date'>;

export const VisioMeetingSchema: yup.ObjectSchema<AddOnlineMeetingFields> = yup
  .object({
    name: yup.string().required().label(t('meeting.form.fields.name')),
    url: yup
      .string()
      .transform((value) => (value?.trim() === '' ? null : value))
      .url(notSupportedErrorMessage.value)
      .nullable()
      .default(null)
      .test(
        'valid-url',
        (urlRef) => selectErrorMessage(urlRef.value),
        (url) => validateUrl(url),
      )
      .label(t('meeting.form.fields.url.label')),
    meeting_password: yup
      .string()
      .transform((value) => (value?.trim() === '' ? null : value))
      .nullable()
      .default(null)
      .min(6)
      .max(8)
      .label(t('meeting.form.fields.external-password')),
    meeting_platform_id: yup
      .string()
      .transform((value) => (value?.trim() === '' ? null : value))
      .nullable()
      .default(null)
      .min(4)
      .label(t('meeting.form.fields.external-id')),
  })
  .test('url_or_id_password', '', function (values, context) {
    const { url, meeting_platform_id, meeting_password } = values || {};

    const hasUrl = url !== null && url !== undefined;
    const hasId = meeting_platform_id !== null && meeting_platform_id !== undefined;
    const hasPassword = meeting_password !== null && meeting_password !== undefined;

    if (hasUrl || (hasId && hasPassword)) {
      return true;
    }

    if (!hasUrl && !hasId && !hasPassword) {
      return context.createError({
        path: 'url',
        message: t('meeting-v2.visio-form.errors.no-field'),
      });
    }

    if (hasId && !hasPassword) {
      return context.createError({
        path: 'meeting_password',
        message: t('meeting-v2.visio-form.errors.id-no-password'),
      });
    }

    if (!hasId && hasPassword) {
      return context.createError({
        path: 'meeting_platform_id',
        message: t('meeting-v2.visio-form.errors.password-no-id'),
      });
    }
  });

export function visioMeetingFieldsToVisioMeetingDto(
  fields: AddOnlineMeetingFields,
): AddOnlineMeetingDto {
  const name_platform = guessPlatformUsingUrl(fields.url);

  const dto: AddOnlineMeetingDto = {
    ...fields,
    name_platform: name_platform,
    creation_date: new Date().toISOString(),
  };

  return dto;
}

function guessPlatformUsingUrl(url: Nullable<string>): OnlineMeetingPlatforms {
  if (url === null) return 'COMU';
  const match = platformConfigs.value.find(({ validator }) => validator.test(url));
  if (match) return match.name;
  throw new Error('Received invalid url to send to meeting');
}

type UpdateNameMeetingFields = { name: string };

export const EditRecordMeetingSchema: yup.ObjectSchema<UpdateNameMeetingFields> = yup.object({
  name: yup.string().required().label(t('meeting.form.fields.name')),
});
