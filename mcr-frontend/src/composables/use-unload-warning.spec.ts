import { describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { computed, defineComponent, ref } from 'vue';
import { useUnloadWarning } from './use-unload-warning';

function mountWithWarning(isActive: ReturnType<typeof ref<boolean>>) {
  return mount(
    defineComponent({
      setup() {
        useUnloadWarning(computed(() => isActive.value === true));
        return () => null;
      },
    }),
  );
}

function dispatchBeforeUnload() {
  const event = new Event('beforeunload', { cancelable: true });
  const preventDefault = vi.spyOn(event, 'preventDefault');
  window.dispatchEvent(event);
  return preventDefault;
}

describe('useUnloadWarning', () => {
  it('prevents unload while active', () => {
    const isActive = ref(true);
    const wrapper = mountWithWarning(isActive);

    expect(dispatchBeforeUnload()).toHaveBeenCalled();
    wrapper.unmount();
  });

  it('stays silent while inactive', () => {
    const isActive = ref(false);
    const wrapper = mountWithWarning(isActive);

    expect(dispatchBeforeUnload()).not.toHaveBeenCalled();
    wrapper.unmount();
  });

  it('removes the listener on unmount', () => {
    const isActive = ref(true);
    const wrapper = mountWithWarning(isActive);
    wrapper.unmount();

    expect(dispatchBeforeUnload()).not.toHaveBeenCalled();
  });
});
