import axios from 'axios';
import { API_BASE } from '../config';
import type { Drill } from '../types';

// The whole library, in pages (#489).
//
// `GET /drills/` with no limit makes the server build every row in memory at once. With ~5,200
// drills it held; on 29-10-2026 the library reached ~8,700 and Render's 512 MB instance died three
// times in an evening, because every opening of the app asked for all of it — twice, once for the
// offline copy and once for the Frases screen. Pages of 500, one after the other, keep each
// request small. A drill created while paging shifts the offsets; ids are deduplicated so it
// never shows twice.

const PAGE = 500;

/** Generic because two `Drill` types live in this app (types.ts and the offline manager's). */
export async function fetchAllDrills<T extends { id: number } = Drill>(): Promise<T[]> {
  const seen = new Set<number>();
  const all: T[] = [];
  for (let offset = 0; ; offset += PAGE) {
    const res = await axios.get<T[]>(`${API_BASE}/drills/`, { params: { limit: PAGE, offset } });
    const page = Array.isArray(res.data) ? res.data : [];
    for (const d of page) {
      if (seen.has(d.id)) continue;
      seen.add(d.id);
      all.push(d);
    }
    const total = Number(res.headers?.['x-total-count']);
    if (page.length < PAGE || (Number.isFinite(total) && offset + PAGE >= total)) break;
  }
  return all;
}
