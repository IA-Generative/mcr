<script setup lang="ts">
import { useSlots } from 'vue';
import { useI18n } from 'vue-i18n';
import { VueFinalModal } from 'vue-final-modal';
import type { DsfrButtonProps, DsfrModalProps } from '@gouvminint/vue-dsfr';
import { useVfm } from 'vue-final-modal';
import { useRandomId } from '@/composables/use-random-id';

type BaseModalProps = {
  title: string;
  text?: string;
  ctaLabel?: string;
  ctaIcon?: string;
  actions?: DsfrButtonProps[];
  modalId?: string;
  noActions?: boolean;
  disableCloseOnOutsideClick?: boolean;
};

const props = defineProps<BaseModalProps & Partial<DsfrModalProps>>();

const emit = defineEmits<{
  (e: 'success'): void;
}>();

const slots = useSlots();
const { t } = useI18n();

const defaultActions: DsfrButtonProps[] = [
  {
    label: props.ctaLabel ?? t('common.yes'),
    icon: props.ctaIcon,
    onClick() {
      emit('success');
      closeModal();
    },
  },
  {
    label: t('common.cancel'),
    tertiary: true,
    noOutline: true,
    onClick() {
      closeModal();
    },
  },
];

const hasFooterSlot = computed(() => !!slots.footer);
const id = computed(() => props.modalId ?? useRandomId('modal-'));
const displayedActions = computed(() => {
  if (props.noActions) {
    return undefined;
  }
  return props.actions ?? defaultActions;
});

const closeModal = () => {
  useVfm().close(id.value);
};

const onClickDsfrModal = (e: MouseEvent) => {
  if (
    e.target instanceof HTMLElement &&
    e.target.matches('dialog.fr-modal') &&
    !props.disableCloseOnOutsideClick
  ) {
    closeModal();
  }
};
</script>

<template>
  <VueFinalModal
    :modal-id="id"
    overlay-class="vfm__overlay--mcr"
  >
    <DsfrModal
      v-bind="props"
      :opened="true"
      :actions="$slots.footer ? [] : displayedActions"
      @click="(e: MouseEvent) => onClickDsfrModal(e)"
      @close="() => closeModal()"
    >
      <template #default>
        <slot>
          <p>{{ text }}</p>
        </slot>
      </template>

      <template
        v-if="hasFooterSlot"
        #footer
      >
        <slot name="footer" />
      </template>
    </DsfrModal>
  </VueFinalModal>
</template>

<style>
.vfm__overlay--mcr {
  background-color: rgba(0, 0, 0, 0);
}

/* Override DSFR modal styles */
.fr-modal__footer {
  margin-top: 0;
  padding-top: 0;
}

.fr-modal__content {
  padding-bottom: 1.5rem;
  margin-bottom: 0;
}

.fr-modal__body {
  display: flex;
  flex-direction: column;
}
</style>
