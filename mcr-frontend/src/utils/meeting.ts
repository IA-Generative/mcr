export function parseWebconfUrl(url: string): string | undefined {
  const webconfUrl = new URL(url);
  const meetingName = webconfUrl.pathname.split('/').pop();
  return meetingName;
}
