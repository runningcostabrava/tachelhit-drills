import { Preferences } from '@capacitor/preferences';
import { Network } from '@capacitor/network';
import { Filesystem, Directory } from '@capacitor/filesystem';
import axios from 'axios';
import { API_BASE, getMediaUrl } from '../config';
import { mimeForFileName } from './../utils/media';

import type { Drill } from '../types';
import { fetchAllDrills } from './fetchAllDrills';

// Re-exported for existing imports (MobileDrillCreator/Editor)
export type { Drill };

export interface SyncAction {
  type: 'CREATE' | 'UPDATE' | 'UPLOAD_MEDIA' | 'DELETE';
  drillId: number;
  payload?: any;
  mediaType?: 'audio' | 'video' | 'image';
  localPath?: string;
  fileName?: string;
  /** Stable id so a sync run can remove exactly the actions it completed. */
  uid?: string;
  /** Failed attempts so far; parked in the dead-letter list at MAX_ATTEMPTS. */
  attempts?: number;
  lastError?: string;
}

const DRILLS_CACHE_KEY = 'cached_drills';
const TESTS_CACHE_KEY = 'cached_tests';
const SYNC_QUEUE_KEY = 'sync_queue';
const DEAD_QUEUE_KEY = 'sync_dead';
const MAX_ATTEMPTS = 5;
/** A media URL that failed to download is not retried before this (a 404 waits a day). */
const MEDIA_RETRY_MS = 60 * 60 * 1000;
const MEDIA_RETRY_404_MS = 24 * 60 * 60 * 1000;
/** A full media walk (one Filesystem.stat per drill asset) runs at most this often. */
const MEDIA_SYNC_MIN_INTERVAL_MS = 10 * 60 * 1000;
const newUid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

class OfflineSyncManager {
  private syncPromise: Promise<void> | null = null;
  /** url -> time before which it must not be downloaded again (dead links, 404s, offline blips). */
  private mediaRetryAfter = new Map<string, number>();
  private lastMediaSyncAt = 0;

  async getDrills(): Promise<Drill[]> {
    const { value } = await Preferences.get({ key: DRILLS_CACHE_KEY });
    return value ? JSON.parse(value) : [];
  }

  // On the web, Preferences is localStorage: about 5 MB for the whole origin, and the library
  // passed that long ago. A cache that cannot be written is a pity, not a failure — losing the
  // offline copy must never look like losing the server, so this never throws. When the whole
  // library does not fit, what a person needs offline is kept (the texts and the media links)
  // and the rest is dropped.
  async saveDrillsToCache(drills: Drill[]) {
    const write = async (value: string) => Preferences.set({ key: DRILLS_CACHE_KEY, value });
    try {
      await write(JSON.stringify(drills));
    } catch {
      const slim = drills.map((d: any) => ({
        id: d.id, text_catalan: d.text_catalan, text_tachelhit: d.text_tachelhit,
        text_arabic: d.text_arabic, audio_url: d.audio_url, image_url: d.image_url,
        tag: d.tag, region: d.region, variety: d.variety, date_created: d.date_created,
      }));
      try {
        await write(JSON.stringify(slim));
        console.warn(`[Sync] Library too big for local storage: kept a light copy of ${slim.length} drills.`);
      } catch {
        try { await Preferences.remove({ key: DRILLS_CACHE_KEY }); } catch { /* nothing to do */ }
        console.warn('[Sync] No room for an offline copy of the drills; the app will always ask the server.');
      }
    }
    // Trigger media sync in background when drills are updated
    this.syncAllMedia();
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

  async getDeadLetters(): Promise<SyncAction[]> {
    const { value } = await Preferences.get({ key: DEAD_QUEUE_KEY });
    return value ? JSON.parse(value) : [];
  }

  private async setDeadLetters(items: SyncAction[]) {
    await Preferences.set({ key: DEAD_QUEUE_KEY, value: JSON.stringify(items) });
  }

  /** Put the dead-letter actions back in the queue and try again. */
  async retryDeadLetters() {
    const dead = await this.getDeadLetters();
    if (!dead.length) return;
    const queue = await this.getQueue();
    for (const a of dead) queue.push({ ...a, attempts: 0, lastError: undefined });
    await Preferences.set({ key: SYNC_QUEUE_KEY, value: JSON.stringify(queue) });
    await this.setDeadLetters([]);
    await this.sync();
  }

  async discardDeadLetters() {
    await this.setDeadLetters([]);
  }

  async queueAction(action: SyncAction) {
    const queue = await this.getQueue();
    action = { ...action, uid: action.uid || newUid(), attempts: action.attempts || 0 };

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
    } else if (action.type === 'DELETE') {
      // Drop every pending action for this drill; if it was created offline
      // and never synced (a CREATE is still queued), the server never heard
      // of it, so no DELETE needs to be sent at all.
      const hadUnsyncedCreate = queue.some(a => a.type === 'CREATE' && a.drillId === action.drillId);
      for (let i = queue.length - 1; i >= 0; i--) {
        if (queue[i].drillId === action.drillId) queue.splice(i, 1);
      }
      if (!hadUnsyncedCreate) {
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

  // Awaitable: concurrent callers share the same in-flight run.
  sync(): Promise<void> {
    if (!this.syncPromise) {
      this.syncPromise = this.doSync().finally(() => {
        this.syncPromise = null;
      });
    }
    return this.syncPromise;
  }

  private async doSync() {
    const status = await Network.getStatus();
    if (!status.connected) return;

    try {
      const { value } = await Preferences.get({ key: SYNC_QUEUE_KEY });
      let queue: SyncAction[] = value ? JSON.parse(value) : [];

      if (queue.length === 0) {
        return;
      }

      console.log(`[Sync] Starting sync for ${queue.length} actions...`);
      // Actions are identified by uid so that anything queued WHILE this run
      // is in progress (long uploads) is never lost when we write back.
      queue = queue.map(a => ({ ...a, uid: a.uid || newUid() }));
      await Preferences.set({ key: SYNC_QUEUE_KEY, value: JSON.stringify(queue) });
      const done = new Set<string>();
      const failed = new Map<string, string>();

      for (const action of queue) {
        try {
          if (action.type === 'CREATE') {
            const res = await axios.post(`${API_BASE}/drills/`, action.payload);
            const serverDrill = res.data;
            // Update the local cache with the real ID
            await this.updateLocalDrillId(action.drillId, serverDrill);
            // Remap the temporary id everywhere: this run's copy AND the
            // persisted queue (which may have gained actions meanwhile)
            this.updateQueueDrillId(queue, action.drillId, serverDrill.id);
            const persisted = await this.getQueue();
            this.updateQueueDrillId(persisted, action.drillId, serverDrill.id);
            await Preferences.set({ key: SYNC_QUEUE_KEY, value: JSON.stringify(persisted) });
          } else if (action.type === 'UPDATE') {
            await axios.put(`${API_BASE}/drills/${action.drillId}`, action.payload);
          } else if (action.type === 'UPLOAD_MEDIA') {
            await this.processMediaUpload(action);
          } else if (action.type === 'DELETE') {
            try {
              await axios.delete(`${API_BASE}/drills/${action.drillId}`);
            } catch (err: any) {
              // Already gone on the server counts as success
              if (err?.response?.status !== 404) throw err;
            }
          }
          done.add(action.uid!);
        } catch (err: any) {
          console.error('[Sync] Action failed:', action, err);
          failed.set(action.uid!, err?.response?.data?.detail || err?.message || 'error');
        }
      }

      // Write back against the CURRENT persisted queue, not our stale copy.
      const fresh = await this.getQueue();
      const dead = await this.getDeadLetters();
      const remaining: SyncAction[] = [];
      for (const a of fresh) {
        if (a.uid && done.has(a.uid)) continue;
        if (a.uid && failed.has(a.uid)) {
          const attempts = (a.attempts || 0) + 1;
          const withErr = { ...a, attempts, lastError: failed.get(a.uid) };
          if (attempts >= MAX_ATTEMPTS) dead.push(withErr); else remaining.push(withErr);
          continue;
        }
        remaining.push(a); // queued during this run: untouched
      }
      await Preferences.set({ key: SYNC_QUEUE_KEY, value: JSON.stringify(remaining) });
      await this.setDeadLetters(dead);

      // Refresh cache after sync
      const [drills, testsRes] = await Promise.all([
        fetchAllDrills(),
        axios.get(`${API_BASE}/tests/`)
      ]);
      await this.saveDrillsToCache(drills);
      await this.saveTestsToCache(testsRes.data);

    } catch (err) {
      console.error('[Sync] Critical error:', err);
    }
  }

  // Removes a drill from the local cache immediately and queues the server
  // delete (skipped entirely for drills created offline that never synced).
  // Resolves once a sync attempt has run, so callers can refresh afterwards.
  async deleteDrill(id: number) {
    const drills = await this.getDrills();
    await Preferences.set({
      key: DRILLS_CACHE_KEY,
      value: JSON.stringify(drills.filter(d => d.id !== id)),
    });
    await this.queueAction({ type: 'DELETE', drillId: id });
    await this.sync();
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
    const blob = new Blob([byteArray], { type: mimeForFileName(action.fileName) });

    const formData = new FormData();
    formData.append('file', blob, action.fileName);

    let res;
    try {
      res = await axios.post(`${API_BASE}/upload-media/${action.drillId}/${action.mediaType}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    } catch (err: any) {
      if (err?.response?.status === 404 || err?.response?.status === 400) {
        // Permanent: mark as exhausted so it goes straight to the dead list
        action.attempts = MAX_ATTEMPTS - 1;
      }
      throw err;
    }

    if (res.data.url) {
      // Cleanup local file
      await Filesystem.deleteFile({
        path: action.localPath,
        directory: Directory.Data
      });
    }
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

  async downloadAndCacheMedia(url: string, mediaType?: 'audio' | 'video' | 'image'): Promise<string> {
    if (!url || url.startsWith('blob:') || url.startsWith('data:')) return url;

    // Auto-detect media type if not provided
    if (!mediaType) {
      if (url.includes('.mp4') || url.includes('.webm')) mediaType = 'video';
      else if (url.includes('.jpg') || url.includes('.jpeg') || url.includes('.png')) mediaType = 'image';
      else if (url.includes('.mp3') || url.includes('.wav') || url.includes('.m4a')) mediaType = 'audio';
    }

    const retryAt = this.mediaRetryAfter.get(url);
    if (retryAt && retryAt > Date.now()) return url;

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

      const fullUrl = getMediaUrl(url);
      console.log(`[OfflineSync] Downloading ${mediaType}: ${fullUrl}`);

      // Use standard fetch if axios fails in some Capacitor environments
      // Use different timeout based on media type
      const timeout = mediaType === 'video' ? 120000 : 60000;
      const response = await axios.get(fullUrl, {
        responseType: 'blob',
        timeout
      });
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
      // Remember the failure: a dead link used to be retried on every drill-list refresh,
      // every few seconds, for as long as the app was open (battery + data on the phone).
      const e = err as { response?: { status?: number }; message?: string } | undefined;
      const status = e?.response?.status;
      const wait = status === 404 || status === 410 ? MEDIA_RETRY_404_MS : MEDIA_RETRY_MS;
      this.mediaRetryAfter.set(url, Date.now() + wait);
      console.warn(`[OfflineSync] Media download failed for ${url} (retry in ${Math.round(wait / 60000)} min):`, e?.message || err);
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

  async syncAllMedia(options?: { includeVideos?: boolean; batchSize?: number; force?: boolean }) {
    // Only perform background sync if running in a regular web browser on localhost OR if in Capacitor environment
    // For production web (Vercel), we don't want to try downloading files to a filesystem that doesn't exist
    const isCapacitor = (window as any).Capacitor?.isNativePlatform();
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

    if (!isCapacitor && !isLocalhost) {
      return;
    }

    const status = await Network.getStatus();
    if (!status.connected) return;

    // The drill list is refreshed often (every page visit, after every change); walking
    // every asset each time is a native-bridge call per asset. Once per interval is plenty.
    if (!options?.force && Date.now() - this.lastMediaSyncAt < MEDIA_SYNC_MIN_INTERVAL_MS) return;

    // Use a lock to prevent concurrent syncAllMedia runs
    if ((this as any).isMediaSyncing) {
      console.log('[OfflineSync] Media sync already in progress, skipping...');
      return;
    }
    (this as any).isMediaSyncing = true;
    this.lastMediaSyncAt = Date.now();

    try {
      const drills = await this.getDrills();
      const includeVideos = options?.includeVideos ?? false; // Don't cache videos by default
      const batchSize = options?.batchSize ?? 3; // Slightly increased batch size since we're being selective

      console.log(`[OfflineSync] Syncing media for ${drills.length} drills (includeVideos: ${includeVideos})...`);

      // Use smaller batches and sequential processing to avoid "AxiosError: Network Error"
      for (let i = 0; i < drills.length; i += batchSize) {
        const batch = drills.slice(i, i + batchSize);
        // Process batch sequentially to avoid connection flooding
        for (const drill of batch) {
          try {
            if (drill.audio_url) await this.downloadAndCacheMedia(drill.audio_url, 'audio');
            if (drill.image_url) await this.downloadAndCacheMedia(drill.image_url, 'image');
            // Only cache videos if explicitly requested - they can be very large
            if (includeVideos && drill.video_url) {
              await this.downloadAndCacheMedia(drill.video_url, 'video');
            }
          } catch (drillErr) {
            console.warn(`[OfflineSync] Failed to sync media for drill ${drill.id}:`, drillErr);
            // Continue with next drill instead of failing the entire batch
          }
        }
        // Small breathing room between batches to avoid overwhelming the connection
        await new Promise(resolve => setTimeout(resolve, 200));
      }
      console.log('[OfflineSync] Media sync complete');
    } catch (err) {
      console.error('[OfflineSync] Media sync failed:', err);
    } finally {
      (this as any).isMediaSyncing = false;
    }
  }
}

export const syncManager = new OfflineSyncManager();
