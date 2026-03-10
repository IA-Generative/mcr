import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { defineComponent } from 'vue';
import { useNetworkStatus } from './use-network-status';

function createTestComponent() {
  return defineComponent({
    setup() {
      const { isOnline } = useNetworkStatus();
      return { isOnline };
    },
    template: '<div>{{ isOnline }}</div>',
  });
}

describe('useNetworkStatus', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('initializes isOnline from navigator.onLine', () => {
    Object.defineProperty(navigator, 'onLine', { value: true, configurable: true });
    const wrapper = mount(createTestComponent());
    expect(wrapper.vm.isOnline).toBe(true);
    wrapper.unmount();
  });

  it('initializes isOnline to false when navigator.onLine is false', () => {
    Object.defineProperty(navigator, 'onLine', { value: false, configurable: true });
    const wrapper = mount(createTestComponent());
    expect(wrapper.vm.isOnline).toBe(false);
    wrapper.unmount();
  });

  it('sets isOnline to false when offline event fires', () => {
    Object.defineProperty(navigator, 'onLine', { value: true, configurable: true });
    const wrapper = mount(createTestComponent());

    window.dispatchEvent(new Event('offline'));
    expect(wrapper.vm.isOnline).toBe(false);
    wrapper.unmount();
  });

  it('sets isOnline to true when online event fires', () => {
    Object.defineProperty(navigator, 'onLine', { value: false, configurable: true });
    const wrapper = mount(createTestComponent());

    window.dispatchEvent(new Event('online'));
    expect(wrapper.vm.isOnline).toBe(true);
    wrapper.unmount();
  });

  it('removes event listeners on unmount', () => {
    Object.defineProperty(navigator, 'onLine', { value: true, configurable: true });
    const addSpy = vi.spyOn(window, 'addEventListener');
    const removeSpy = vi.spyOn(window, 'removeEventListener');

    const wrapper = mount(createTestComponent());

    const onlineHandler = addSpy.mock.calls.find((c) => c[0] === 'online')![1];
    const offlineHandler = addSpy.mock.calls.find((c) => c[0] === 'offline')![1];

    wrapper.unmount();

    expect(removeSpy).toHaveBeenCalledWith('online', onlineHandler);
    expect(removeSpy).toHaveBeenCalledWith('offline', offlineHandler);
  });
});
