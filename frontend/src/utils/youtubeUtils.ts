export function getYouTubeVideoId(url: string): string | null {
  if (!url) return null;
  try {
    const urlObj = new URL(url);
    if (urlObj.hostname === 'www.youtube.com' || urlObj.hostname === 'youtube.com') {
      return urlObj.searchParams.get('v');
    } else if (urlObj.hostname === 'youtu.be') {
      return urlObj.pathname.slice(1);
    }
  } catch (e) {
    // console.error("Invalid URL:", url, e);
  }
  return null;
}

export function isYouTubeUrl(url: string): boolean {
  if (!url) return false;
  return url.includes('youtube.com') || url.includes('youtu.be');
}

export function getYouTubeEmbedUrl(url: string): string {
  if (!url) return '';
  
  try {
    const videoId = getYouTubeVideoId(url);
    if (!videoId) return url;
    
    const urlObj = new URL(url);
    const timestamp = urlObj.searchParams.get('t') || urlObj.searchParams.get('start') || '';
    
    let embedUrl = `https://www.youtube.com/embed/${videoId}?loop=1&playlist=${videoId}`;
    
    let startTime = 0;
    if (timestamp) {
      if (timestamp.includes('h') || timestamp.includes('m') || timestamp.includes('s')) {
        const timeRegex = /(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?/;
        const match = timestamp.match(timeRegex);
        if (match) {
          const hours = parseInt(match[1] || '0');
          const minutes = parseInt(match[2] || '0');
          const secs = parseInt(match[3] || '0');
          startTime = hours * 3600 + minutes * 60 + secs;
        }
      } else {
        startTime = parseInt(timestamp) || 0;
      }
    } else {
      startTime = parseInt(urlObj.searchParams.get('start') || '0');
    }

    if (startTime > 0) {
      embedUrl += `&start=${startTime}`;
    }

    const endTime = urlObj.searchParams.get('end');
    if (endTime) {
      embedUrl += `&end=${endTime}`;
    }
    
    return embedUrl;
  } catch (error) {
    return url.replace('watch?v=', 'embed/').replace('youtu.be/', 'youtube.com/embed/');
  }
}
