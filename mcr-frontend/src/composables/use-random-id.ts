export function useRandomId(prefix = '') {
  return (prefix ? `${prefix}-` : '') + useId();
}
