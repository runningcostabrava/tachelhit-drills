import { Preferences } from '@capacitor/preferences';
import { Network } from '@capacitor/network';
import { Filesystem, Directory } from '@capacitor/filesystem';
import axios from 'axios';
import { API_BASE, getMediaUrl } from '../config';

export interface Drill {
  id: number;
  text_catalan?: string;
  text_tachelhit?: string;
  text_arabic?: string;
  audio_url?: string;
  video_url?: string;
  image_url?: string;
  tag?: string;
  author?: string;
  date_created: string;
  is_local?: boolean; // Marker for locally created drills
}

export interface SyncAction {
  type: 'CREATE' | 'UPDATE' | 'UPLOAD_MEDIA';
  drillId: number;
  payload?: any;
  mediaType?: 'audio' | 'video' | 'image';
  localPath?: string;
  fileName?: string;
}

const DRILLS_CACHE_KEY = 'cached_drills';
const TESTS_CACHE_KEY = 'cached_tests';
const SYNC_QUEUE_KEY = 'sync_queue';

class OfflineSyncManager {
  private isSyncing = false;

  async getDrills(): Promise<Drill[]> {
    const { value } = await Preferences.get({ key: DRILLS_CACHE_KEY });
    return value ? JSON.parse(value) : [];
  }

  async saveDrillsToCache(drills: Drill[]) {
    await Preferences.set({
      key: DRILLS_CACHE_KEY,
      value: JSON.stringify(drills),
    });
  }

  async getTests(): Promise<any[]> {
    const { value } = await Preferences.get({ key: TESTS_CACHE_KEY });
    return value ? JSON.parse(value) : [];
  }

  async saveTestsToCache(tests: any[]) {
    await Preferences.set({
      key: TESTS_CACHE_KEY,
      value: JSON.stringify(tests),
    });
  }

  async getQueue(): Promise<SyncAction[]> {
    const { value } = await Preferences.get({ key: SYNC_QUEUE_KEY });
    return value ? JSON.parse(value) : [];
  }

  async queueAction(action: SyncAction) {
    const queue = await this.getQueue();
    
    // Deduplication / Merging logic
    if (action.type === 'CREATE') {
      // Check if we already have a CREATE for this temporary drill ID
      const existingIdx = queue.findIndex(a => a.type === 'CREATE' && a.drillId === action.drillId);
      if (existingIdx > -1) {
        queue[existingIdx].payload = { ...queue[existingIdx].payload, ...action.payload };
      } else {
        queue.push(action);
      }
    } else if (action.type === 'UPDATE') {
      // If there's already a CREATE in queue for this drill, just update its payload
      const createIdx = queue.findIndex(a => a.type === 'CREATE' && a.drillId === action.drillId);
      if (createIdx > -1) {
        queue[createIdx].payload = { ...queue[createIdx].payload, ...action.payload };
      } else {
        // Otherwise look for existing UPDATE or just add new
        const existingIdx = queue.findIndex(a => a.type === 'UPDATE' && a.drillId === action.drillId);
        if (existingIdx > -1) {
          queue[existingIdx].payload = { ...queue[existingIdx].payload, ...action.payload };
        } else {
          queue.push(action);
        }
      }
    } else if (action.type === 'UPLOAD_MEDIA') {
      // Avoid duplicate media uploads for same drill and type in queue
      const existingIdx = queue.findIndex(a => a.type === 'UPLOAD_MEDIA' && a.drillId === action.drillId && a.mediaType === action.mediaType);
      if (existingIdx > -1) {
        queue[existingIdx] = action; // Replace with newest path
      } else {
        queue.push(action);
      }
    } else {
      queue.push(action);
    }

    await Preferences.set({
      key: SYNC_QUEUE_KEY,
      value: JSON.stringify(queue),
    });
    
    // Try to sync if online
    this.sync();
  }

  async sync() {
    if (this.isSyncing) return;
    const status = await Network.getStatus();
    if (!status.connected) return;

    this.isSyncing = true;
    try {
      const { value } = await Preferences.get({ key: SYNC_QUEUE_KEY });
      let queue: SyncAction[] = value ? JSON.parse(value) : [];

      if (queue.length === 0) {
        this.isSyncing = false;
        return;
      }

      console.log(`[Sync] Starting sync for ${queue.length} actions...`);
      const remainingQueue: SyncAction[] = [];

      for (const action of queue) {
        try {
          if (action.type === 'CREATE') {
            const res = await axios.post(`${API_BASE}/drills/`, action.payload);
            const serverDrill = res.data;
            // Update the local cache with the real ID
            await this.updateLocalDrillId(action.drillId, serverDrill);
            // Update other actions in queue that refer to this temporary ID
            this.updateQueueDrillId(queue, action.drillId, serverDrill.id);
          } else if (action.type === 'UPDATE') {
            await axios.put(`${API_BASE}/drills/${action.drillId}`, action.payload);
          } else if (action.type === 'UPLOAD_MEDIA') {
            await this.processMediaUpload(action);
          }
        } catch (err) {
          console.error('[Sync] Action failed:', action, err);
          remainingQueue.push(action); // Keep failed actions for next try
        }
      }

      await Preferences.set({
        key: SYNC_QUEUE_KEY,
        value: JSON.stringify(remainingQueue),
      });

      // Refresh cache after sync
      const [drillsRes, testsRes] = await Promise.all([
        axios.get(`${API_BASE}/drills/`),
        axios.get(`${API_BASE}/tests/`)
      ]);
      await this.saveDrillsToCache(drillsRes.data);
      await this.saveTestsToCache(testsRes.data);

    } catch (err) {
      console.error('[Sync] Critical error:', err);
    } finally {
      this.isSyncing = false;
    }
  }

  private async updateLocalDrillId(oldId: number, serverData: Drill) {
    const drills = await this.getDrills();
    const idx = drills.findIndex(d => d.id === oldId);
    if (idx > -1) {
      drills[idx] = { ...serverData, is_local: false };
      await this.saveDrillsToCache(drills);
    }
  }

  private updateQueueDrillId(queue: SyncAction[], oldId: number, newId: number) {
    for (const action of queue) {
      if (action.drillId === oldId) {
        action.drillId = newId;
      }
    }
  }

  private async processMediaUpload(action: SyncAction) {
    if (!action.localPath || !action.fileName || !action.mediaType) return;

    // Read the file from local storage
    const file = await Filesystem.readFile({
      path: action.localPath,
      directory: Directory.Data
    });

    // Convert base64 to Blob
    const byteCharacters = atob(file.data as string);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: this.getMimeType(action.fileName) });

    const formData = new FormData();
    formData.append('file', blob, action.fileName);

    const res = await axios.post(`${API_BASE}/upload-media/${action.drillId}/${action.mediaType}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });

    if (res.data.url) {
      // Cleanup local file
      await Filesystem.deleteFile({
        path: action.localPath,
        directory: Directory.Data
      });
    }
  }

  private getMimeType(fileName: string): string {
    if (fileName.endsWith('.jpg') || fileName.endsWith('.jpeg')) return 'image/jpeg';
    if (fileName.endsWith('.mp4')) return 'video/mp4';
    if (fileName.endsWith('.webm')) return 'video/webm';
    if (fileName.endsWith('.m4a')) return 'audio/mp4';
    if (fileName.endsWith('.wav')) return 'audio/wav';
    return 'application/octet-stream';
  }

  async saveMediaLocally(blob: Blob, fileName: string): Promise<string> {
    const base64Data = await this.blobToBase64(blob);
    const result = await Filesystem.writeFile({
      path: fileName,
      data: base64Data,
      directory: Directory.Data
    });
    return result.uri;
  }

  private blobToBase64(blob: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64String = (reader.result as string).split(',')[1];
        resolve(base64String);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  async downloadAndCacheMedia(url: string): Promise<string> {
    if (!url || url.startsWith('blob:') || url.startsWith('data:')) return url;
    
    try {
      const fileName = url.split('/').pop() || `media_${Date.now()}`;
      
      // Check if already exists
      try {
        const stat = await Filesystem.stat({
          path: `media/${fileName}`,
          directory: Directory.Data
        });
        return (window as any).Capacitor.convertFileSrc(stat.uri);
      } catch (e) {
        // Doesn't exist, download it
      }

      const response = await axios.get(getMediaUrl(url), { responseType: 'blob' });
      const base64Data = await this.blobToBase64(response.data);
      
      await Filesystem.writeFile({
        path: `media/${fileName}`,
        data: base64Data,
        directory: Directory.Data,
        recursive: true
      });

      const result = await Filesystem.getUri({
        path: `media/${fileName}`,
        directory: Directory.Data
      });
      
      return (window as any).Capacitor.convertFileSrc(result.uri);
    } catch (err) {
      console.error('Media download failed:', err);
      return url;
    }
  }

  async getLocalMediaUrl(url: string): Promise<string> {
    if (!url || url.startsWith('blob:') || url.startsWith('data:')) return url;
    try {
      const fileName = url.split('/').pop();
      const stat = await Filesystem.stat({
        path: `media/${fileName}`,
        directory: Directory.Data
      });
      return (window as any).Capacitor.convertFileSrc(stat.uri);
    } catch (e) {
      return getMediaUrl(url);
    }
  }

  async syncAllMedia() {
    const status = await Network.getStatus();
    if (!status.connected) return;

    try {
      const drills = await this.getDrills();
      console.log(`[OfflineSync] Syncing media for ${drills.length} drills...`);
      
      for (const drill of drills) {
        if (drill.audio_url) await this.downloadAndCacheMedia(drill.audio_url);
        if (drill.video_url) await this.downloadAndCacheMedia(drill.video_url);
        if (drill.image_url) await this.downloadAndCacheMedia(drill.image_url);
      }
      console.log('[OfflineSync] Media sync complete');
    } catch (err) {
      console.error('[OfflineSync] Media sync failed:', err);
    }
  }
}

export const syncManager = new OfflineSyncManager();
