export function arrayToMap<T extends Record<string, any>>(
  arr: T[],
  identifier = 'id',
): Map<string | number, T> {
  const map = new Map();
  arr.forEach((item) => map.set(item[identifier], item));
  return map;
}
