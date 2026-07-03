let ytApiPromise: Promise<any> | null = null;

/**
 * Loads the YouTube IFrame API exactly once, no matter how many components
 * request it (DrillPlayer, DrillCard, VideoLibraryPlayer, ...). Resolves with
 * `window.YT` once `YT.Player` is usable. Chains any pre-existing
 * `onYouTubeIframeAPIReady` instead of clobbering it.
 */
export function loadYouTubeApi(): Promise<any> {
  const w = window as any;
  if (w.YT?.Player) return Promise.resolve(w.YT);
  if (ytApiPromise) return ytApiPromise;

  ytApiPromise = new Promise(resolve => {
    const prev = w.onYouTubeIframeAPIReady;
    w.onYouTubeIframeAPIReady = () => {
      if (prev) prev();
      resolve(w.YT);
    };
    if (!document.getElementById('youtube-iframe-api')) {
      const tag = document.createElement('script');
      tag.id = 'youtube-iframe-api';
      tag.src = 'https://www.youtube.com/iframe_api';
      document.head.appendChild(tag);
    }
  });
  return ytApiPromise;
}

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
