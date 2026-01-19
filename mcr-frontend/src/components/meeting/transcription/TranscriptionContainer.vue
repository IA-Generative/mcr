<template>
  <DsfrTabs
    v-model="currentTab"
    tab-list-name=""
    :tab-titles="[]"
    class="m-0 p-0"
  >
    <template #tab-items>
      <DsfrTabItem
        v-for="(tab, index) of tabTitles"
        :key="tab.tabId"
        :tab-id="tab.tabId"
        :panel-id="tab.panelId"
        :icon="tab.icon"
        @click="currentTab = index"
      >
        {{ tab.title }}
      </DsfrTabItem>
    </template>
    <DsfrTabContent
      panel-id="tab-content-0"
      tab-id="tab-0"
      class="flex flex-col justify-center items-center"
    >
      <TranscriptionActions
        :meeting="meeting"
        class="py-24"
      ></TranscriptionActions>
    </DsfrTabContent>

    <DsfrTabContent
      panel-id="tab-content-2"
      tab-id="tab-2"
    >
      <GenerateReportAction :meeting="meeting" />
    </DsfrTabContent>
  </DsfrTabs>
</template>

<script setup lang="ts">
import { type MeetingDto } from '@/services/meetings/meetings.types';
import type { DsfrTabItemProps } from '@gouvminint/vue-dsfr';
import { useI18n } from 'vue-i18n';

defineProps<{
  meeting: MeetingDto;
}>();

const { t } = useI18n();
const currentTab = ref(0);

const tabTitles: (DsfrTabItemProps & { title: string })[] = [
  { title: t('meeting.transcription.tab.transcription'), tabId: 'tab-0', panelId: 'tab-content-0' },
  { title: t('meeting.transcription.tab.report'), tabId: 'tab-2', panelId: 'tab-content-2' },
];
</script>
