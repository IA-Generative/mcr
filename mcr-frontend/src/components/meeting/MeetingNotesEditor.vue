<template>
  <div class="flex flex-col gap-3 border border-grey-900 bg-white p-6">
    <h2 class="text-2xl font-bold text-blue-france-sun">
      {{ $t('meeting-v2.notes.title') }}
    </h2>
    <p class="fr-text--sm m-0 text-grey-200">
      {{ $t('meeting-v2.notes.description') }}
    </p>

    <TipTapEditor
      :model-value="note"
      :placeholder="$t('meeting-v2.notes.placeholder')"
      @update:model-value="onUpdate"
    />
    <div class="flex h-2 justify-end">
      <Transition name="fade">
        <span
          v-if="syncStatus !== 'idle'"
          class="text-xs"
          :class="statusClass"
        >
          {{ statusLabel }}
        </span>
      </Transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { t } from '@/plugins/i18n';
import { useMeetingNotes } from '@/services/meetings/use-meeting-notes';

const props = defineProps<{
  meetingId: number;
  notes?: string | null;
}>();

const { note, syncStatus, onUpdate } = useMeetingNotes(props.meetingId, props.notes);

const statusLabel = computed(() => {
  switch (syncStatus.value) {
    case 'pending':
      return t('meeting-v2.notes.sync.pending');
    case 'saved':
      return t('meeting-v2.notes.sync.saved');
    default:
      return '';
  }
});

const statusClass = computed(() =>
  syncStatus.value === 'saved' ? 'text-success-425' : 'text-info-425',
);
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
