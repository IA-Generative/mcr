export async function isStorageReachable(url: string, timeoutMs = 3000): Promise<boolean> {
  try {
    await fetch(new URL(url).origin, {
      method: 'HEAD',
      mode: 'no-cors',
      signal: AbortSignal.timeout(timeoutMs),
    });

    return true;
  } catch {
    return false;
  }
}
