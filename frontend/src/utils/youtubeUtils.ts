export function getYouTubeVideoId(url: string): string | null {
  const regExp = /(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/(?:watch\?v=|embed/|v/|)([^&?#]+)/;
  const match = url.match(regExp);
  return (match && match[1].length === 11) ? match[1] : null;
}
