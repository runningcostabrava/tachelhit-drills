import { Preferences } from '@capacitor/preferences';
import { Network } from '@capacitor/network';
import { Filesystem, Directory } from '@capacitor/filesystem';
import axios from 'axios';
import { API_BASE } from '../config';

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

  async queueAction(action: SyncAction) {
    const { value } = await Preferences.get({ key: SYNC_QUEUE_KEY });
    const queue: SyncAction[] = value ? JSON.parse(value) : [];
    
    // For UPDATES, if an update for this drill already exists in queue, merge it
    if (action.type === 'UPDATE') {
      const existingIdx = queue.findIndex(a => a.type === 'UPDATE' && a.drillId === action.drillId);
      if (existingIdx > -1) {
        queue[existingIdx].payload = { ...queue[existingIdx].payload, ...action.payload };
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
            await this.updateLocalDrillId(action.drillId, serverDrill.id, serverDrill);
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
      const res = await axios.get(`${API_BASE}/drills/`);
      await this.saveDrillsToCache(res.data);

    } catch (err) {
      console.error('[Sync] Critical error:', err);
    } finally {
      this.isSyncing = false;
    }
  }

  private async updateLocalDrillId(oldId: number, newId: number, serverData: Drill) {
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
}

export const syncManager = new OfflineSyncManager();
