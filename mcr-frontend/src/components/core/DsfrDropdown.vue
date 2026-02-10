<template>
  <section
    v-on-click-outside="handleOutsideClick"
    class="fr-dropdown-menu relative inline-block"
  >
    <DsfrButton
      v-bind="mainButton"
      class="fr-accordion__btn fr-btn"
      :aria-expanded="isActive"
      :aria-controls="id"
      @click="expand()"
    />
    <div
      :id="id"
      ref="collapse"
      class="fr-collapse fr-dropdown-collapse w-full"
      :class="{
        'fr-collapse--expanded': cssExpanded,
        'fr-collapsing': collapsing,
      }"
      @transitionend="onTransitionEnd(isActive)"
    >
      <DsfrButtonGroup
        v-if="buttons.length"
        :buttons="buttonsDropdown"
        :size="dropdownSize"
        inline-layout-when="never"
        class="divide-y border-default-grey"
        equisized
      />
    </div>
  </section>
</template>

<script lang="ts" setup>
import { ref, watch, type ButtonHTMLAttributes } from 'vue';

import { useCollapsable } from '@gouvminint/vue-dsfr';
import type { DsfrButtonProps } from '@gouvminint/vue-dsfr';
import { vOnClickOutside } from '@vueuse/components';
import { useRandomId } from '@/composables/use-random-id';

const id = useRandomId('dropdown-menu');

export type DsfrDropdownProps = {
  mainButton: DsfrButtonProps;
  buttons: (DsfrButtonProps & ButtonHTMLAttributes)[];
};

const props = defineProps<DsfrDropdownProps>();

const dropdownSize = computed(() =>
  props.mainButton.size !== '' ? props.mainButton.size : undefined,
);

const buttonsDropdown = computed(() => {
  return props.buttons.map((button) => ({
    ...button,
    iconOnly: false,
    iconRight: false,
    secondary: false,
    tertiary: true,
    noOutline: true,
  }));
});

const { collapse, collapsing, cssExpanded, doExpand, onTransitionEnd } = useCollapsable();

const isActive = ref(false);

function expand() {
  isActive.value = !isActive.value;
  doExpand(isActive.value);
}

function handleOutsideClick() {
  if (isActive.value) {
    isActive.value = false;
  }
}

watch(isActive, (newValue, oldValue) => {
  if (newValue !== oldValue) {
    doExpand(newValue);
  }
});
</script>

<style>
.fr-dropdown-collapse {
  box-sizing: content-box;
  box-shadow: 0px 4px 12px rgba(0, 0, 18, 0.12);
  position: absolute;
  right: 0;
  top: 100%;
  z-index: 1000;
  background: white;
  min-width: max-content;
}

.fr-dropdown-menu {
  & .fr-btns-group {
    display: flex;
    flex-direction: column;
    min-width: max-content;

    /* Property is defined inline in Dsfr component, hence !important is necessary to override */
    margin-bottom: 0px !important;
    margin-left: 2px;

    & .fr-btn {
      margin: 0;
      padding: 1rem 1.5rem;
      justify-content: flex-start;
      text-align: start;
      min-width: 100%;
      max-width: 282px !important;
    }
  }

  & .fr-accordion__btn[aria-expanded='true'] {
    background-color: var(--background-action-high-blue-france);
    color: var(--text-inverted-blue-france);
    --hover: var(--background-action-high-blue-france-hover);
    --active: var(--background-action-high-blue-france-active);
  }

  & .fr-accordion__btn[aria-expanded='true']:hover {
    background-color: var(--background-action-high-blue-france-active);
  }
}
</style>
