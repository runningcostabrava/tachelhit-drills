// Why it failed, in a sentence the person can act on (#196).
//
// «Alguna cosa ha anat malament» is the one answer that never helps: being throttled, being
// logged out and being offline are three different problems with three different things to do
// about them. This lived inside PracticeEditor; it is here because the screens that create a
// practice reach the API through axios instead of the typed client, and they were swallowing the
// server's own sentence — a visitor without a name was told «no s'ha pogut crear el test» when
// what the server had said was «fes-te un nom al perfil».
//
// Both shapes are read: the typed client in api.ts puts `status` on the error it throws, and
// axios hangs the response off `response` with FastAPI's `detail` inside it.

type MaybeAxios = {
  status?: number;
  message?: string;
  response?: { status?: number; data?: { detail?: unknown } };
};

/** The server's own words when it gave any, else a sentence about what went wrong, else `doing`. */
export function whyItFailed(e: unknown, doing: string): string {
  const err = (e || {}) as MaybeAxios;
  const status = err.response?.status ?? err.status;
  const detail = err.response?.data?.detail;
  // A message written for this very case beats anything generic we could say instead.
  if (typeof detail === 'string' && detail.trim() && !/^[a-z_]+$/i.test(detail.trim())) return detail;
  if (status === 429) return 'El servidor ens frena un moment (massa peticions seguides). Torna-ho a provar d’aquí a un minut.';
  if (status === 401) return 'Per a això et cal un nom. Fes-te’n un al teu perfil.';
  if (status === 403) return 'Això no és teu: demana-ho a qui ho administra.';
  if (status === 404) return 'Això ja no hi és.';
  if (status && status >= 500) return 'El servidor no respon bé ara mateix. Espera una mica i torna-hi.';
  if (status === undefined) return 'No s’ha pogut arribar al servidor. Mira la connexió.';
  return err.message || doing;
}
