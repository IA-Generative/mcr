import yup from '@/config/yup';
import {
  type AddImportMeetingDto,
  type AddImportMeetingDtoAndFile,
} from '@/services/meetings/meetings.types';
import { t } from '@/plugins/i18n';
import { useFeatureFlag } from '@/composables/use-feature-flag';

type AddImportMeetingFields = Omit<AddImportMeetingDto, 'name_platform' | 'creation_date'> & {
  file: File;
};

const MAX_FILE_SIZE = 200_000_000;

export const ImportMeetingSchema: yup.ObjectSchema<AddImportMeetingFields> = yup.object({
  name: yup.string().required().label(t('meeting.import-form.fields.name')),
  file: yup
    .mixed<File>()
    .label(t('meeting.import-form.fields.file.label'))
    .required()
    .test('fileSize', t('meeting.import-form.errors.file-size'), (value) => {
      return isMultipartUploadEnabled() || value.size <= MAX_FILE_SIZE;
    }),
});

export function importMeetingFieldsToMeetingDto(
  fields: AddImportMeetingFields,
): AddImportMeetingDto {
  return {
    name: fields.name,
    name_platform: 'MCR_IMPORT',
    creation_date: new Date().toISOString(),
  };
}

export function importMeetingFieldsToMeetingDtoAndFile(
  fields: AddImportMeetingFields,
): AddImportMeetingDtoAndFile {
  return {
    dto: importMeetingFieldsToMeetingDto(fields),
    file: fields.file,
  };
}

export function isMultipartUploadEnabled(): boolean {
  return useFeatureFlag('multipart-file').value;
}
