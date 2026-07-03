/**
 * Offline Cache Utility for Tachelhit Drills
 *
 * This module provides offline caching for drill data and media files.
 * Uses Cache API for media files and IndexedDB for drill metadata.
 */

const CACHE_NAME = 'tachelhit-drills-v1';
const DB_NAME = 'tachelhit-drills-db';
const DB_VERSION = 1;
const STORE_NAME = 'drills';

// Types
import type { Drill } from '../types';

export type { Drill };

export interface CachedDrill extends Drill {
    _cachedAt: number;
    _audioBlob?: Blob;
    _imageBlob?: Blob;
    _videoBlob?: Blob;
}

// Cache API for media files
export class MediaCache {
    static async openCache(): Promise<Cache> {
        return await caches.open(CACHE_NAME);
    }

    static async cacheMedia(url: string, response: Response): Promise<void> {
        try {
            const cache = await this.openCache();
            await cache.put(url, response.clone());
            console.log(`✅ Cached media: ${url}`);
        } catch (error) {
            console.error(`❌ Failed to cache media ${url}:`, error);
        }
    }

    static async getMedia(url: string): Promise<Response | undefined> {
        try {
            const cache = await this.openCache();
            const response = await cache.match(url);
            if (response) {
                console.log(`✅ Retrieved from cache: ${url}`);
                return response;
            }
        } catch (error) {
            console.error(`❌ Failed to get cached media ${url}:`, error);
        }
        return undefined;
    }

    static async cacheMediaFromUrl(url: string): Promise<boolean> {
        try {
            const response = await fetch(url);
            if (response.ok) {
                await this.cacheMedia(url, response);
                return true;
            }
        } catch (error) {
            console.error(`❌ Failed to fetch and cache ${url}:`, error);
        }
        return false;
    }

    static async clearCache(): Promise<void> {
        try {
            await caches.delete(CACHE_NAME);
            console.log('✅ Cleared media cache');
        } catch (error) {
            console.error('❌ Failed to clear cache:', error);
        }
    }

    static async getCacheSize(): Promise<number> {
        try {
            const cache = await this.openCache();
            const keys = await cache.keys();
            return keys.length;
        } catch (error) {
            console.error('❌ Failed to get cache size:', error);
            return 0;
        }
    }
}

// IndexedDB for drill metadata
export class DrillDatabase {
    private db: IDBDatabase | null = null;

    async open(): Promise<IDBDatabase> {
        return new Promise((resolve, reject) => {
            if (this.db) {
                resolve(this.db);
                return;
            }

            const request = indexedDB.open(DB_NAME, DB_VERSION);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                this.db = request.result;
                resolve(this.db);
            };

            request.onupgradeneeded = (event) => {
                const db = (event.target as IDBOpenDBRequest).result;
                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' });
                    store.createIndex('cachedAt', '_cachedAt');
                    store.createIndex('tag', 'tag');
                }
            };
        });
    }

    async close(): Promise<void> {
        if (this.db) {
            this.db.close();
            this.db = null;
        }
    }

    async saveDrills(drills: Drill[]): Promise<void> {
        const db = await this.open();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction([STORE_NAME], 'readwrite');
            const store = transaction.objectStore(STORE_NAME);

            const cachedDrills: CachedDrill[] = drills.map(drill => ({
                ...drill,
                _cachedAt: Date.now()
            }));

            let completed = 0;
            const total = cachedDrills.length;

            if (total === 0) {
                resolve();
                return;
            }

            cachedDrills.forEach(drill => {
                const request = store.put(drill);
                request.onsuccess = () => {
                    completed++;
                    if (completed === total) {
                        resolve();
                    }
                };
                request.onerror = () => reject(request.error);
            });

            transaction.onerror = () => reject(transaction.error);
        });
    }

    async getDrills(): Promise<CachedDrill[]> {
        const db = await this.open();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction([STORE_NAME], 'readonly');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.getAll();

            request.onsuccess = () => resolve(request.result || []);
            request.onerror = () => reject(request.error);
        });
    }

    async getDrill(id: number): Promise<CachedDrill | undefined> {
        const db = await this.open();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction([STORE_NAME], 'readonly');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.get(id);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async clearDrills(): Promise<void> {
        const db = await this.open();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction([STORE_NAME], 'readwrite');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.clear();

            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    async getDrillCount(): Promise<number> {
        const db = await this.open();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction([STORE_NAME], 'readonly');
            const store = transaction.objectStore(STORE_NAME);
            const request = store.count();

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }
}

// Main offline manager
export class OfflineManager {
    private drillDB = new DrillDatabase();

    async cacheDrillsForOffline(drills: Drill[], getMediaUrl: (url: string) => string): Promise<{ success: boolean; cachedMedia: number; errors: string[] }> {
        const errors: string[] = [];
        let cachedMedia = 0;

        try {
            // Save drill metadata
            await this.drillDB.saveDrills(drills);
            console.log(`✅ Saved ${drills.length} drills to IndexedDB`);

            // Cache media files
            const mediaUrls: string[] = [];

            drills.forEach(drill => {
                if (drill.audio_url) mediaUrls.push(getMediaUrl(drill.audio_url));
                if (drill.audio_tts_url) mediaUrls.push(getMediaUrl(drill.audio_tts_url));
                if (drill.video_url) mediaUrls.push(getMediaUrl(drill.video_url));
                if (drill.image_url) mediaUrls.push(getMediaUrl(drill.image_url));
            });

            // Remove duplicates
            const uniqueUrls = [...new Set(mediaUrls)];

            console.log(`📥 Caching ${uniqueUrls.length} media files...`);

            // Cache each media file
            for (const url of uniqueUrls) {
                try {
                    const success = await MediaCache.cacheMediaFromUrl(url);
                    if (success) {
                        cachedMedia++;
                    } else {
                        errors.push(`Failed to cache: ${url}`);
                    }
                } catch (error) {
                    errors.push(`Error caching ${url}: ${error}`);
                }
            }

            return {
                success: errors.length === 0,
                cachedMedia,
                errors
            };

        } catch (error) {
            errors.push(`Failed to cache drills: ${error}`);
            return {
                success: false,
                cachedMedia,
                errors
            };
        }
    }

    async getOfflineDrills(): Promise<CachedDrill[]> {
        try {
            const drills = await this.drillDB.getDrills();
            console.log(`📊 Retrieved ${drills.length} drills from offline storage`);
            return drills;
        } catch (error) {
            console.error('❌ Failed to get offline drills:', error);
            return [];
        }
    }

    async getMediaFromCache(url: string): Promise<Response | undefined> {
        return await MediaCache.getMedia(url);
    }

    async isOnline(): Promise<boolean> {
        return navigator.onLine;
    }

    async getOfflineStatus(): Promise<{
        hasOfflineData: boolean;
        drillCount: number;
        cacheSize: number;
        lastUpdated?: number;
    }> {
        try {
            const drills = await this.getOfflineDrills();
            const cacheSize = await MediaCache.getCacheSize();

            const lastUpdated = drills.length > 0
                ? Math.max(...drills.map(d => d._cachedAt))
                : undefined;

            return {
                hasOfflineData: drills.length > 0,
                drillCount: drills.length,
                cacheSize,
                lastUpdated
            };
        } catch (error) {
            console.error('❌ Failed to get offline status:', error);
            return {
                hasOfflineData: false,
                drillCount: 0,
                cacheSize: 0
            };
        }
    }

    async clearAllOfflineData(): Promise<void> {
        try {
            await this.drillDB.clearDrills();
            await MediaCache.clearCache();
            console.log('✅ Cleared all offline data');
        } catch (error) {
            console.error('❌ Failed to clear offline data:', error);
            throw error;
        }
    }
}

// Singleton instance
export const offlineManager = new OfflineManager();

// Utility function to check if we should use offline data
export async function getMediaWithOfflineFallback(url: string, getMediaUrl: (url: string) => string): Promise<string> {
    const fullUrl = getMediaUrl(url);

    // Check if we're online
    if (navigator.onLine) {
        // Try to fetch fresh and cache it
        try {
            const response = await fetch(fullUrl);
            if (response.ok) {
                await MediaCache.cacheMedia(fullUrl, response.clone());
                return fullUrl;
            }
        } catch (error) {
            console.warn(`⚠️ Online fetch failed for ${fullUrl}, trying offline cache...`);
        }
    }

    // Try offline cache
    const cachedResponse = await MediaCache.getMedia(fullUrl);
    if (cachedResponse) {
        return URL.createObjectURL(await cachedResponse.blob());
    }

    // Return original URL as fallback
    return fullUrl;
}
