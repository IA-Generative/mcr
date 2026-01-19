<template>
  <BaseModal
    :title="title ?? $t('common.modal.confirm-title.delete')"
    :cta-label="$t('common.modal.confirm-title.delete-button')"
    cta-icon="ri-delete-bin-line"
    is-alert
    @success="$emit('success')"
  ></BaseModal>
</template>

<script setup lang="ts">
defineProps<{
  title?: string;
}>();

defineEmits<{ (e: 'success'): void }>();
</script>
