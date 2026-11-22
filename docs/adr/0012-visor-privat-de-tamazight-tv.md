# 0012 · Un visor privat de Tamazight TV, només per a administradors

**Data:** 19-11-2026 · **Estat:** acceptat (a petició d'en Pablo, per poder-lo ensenyar a la SNRT)

## Problema
Tenim el text (tifinag, àrab, català de màquina) i els temps de 40 capítols de Tamazight TV (SNRT), llegits dels subtítols
cremats. En Pablo vol poder veure els episodis amb subtítols en català i ensenyar el resultat a la SNRT, sense posar res al catàleg públic
(`docs/PERMISOS.md`: recerca sí, republicar no).

## Opcions
1. Space privat d'HuggingFace (no toca la producció).
2. **Rutes d'administrador dins l'app (triada per en Pablo).**
3. Pàgina privada de claude.ai.

## Decisió
Dues taules noves (`snrt_episodes`, `snrt_cues`) només amb text i temps; tres rutes `/snrt-privat/…` que demanen `require_admin`;
pàgina `/snrt`. El vídeo no es guarda ni es serveix: s'encasta de YouTube quan l'episodi hi és, o es carrega des de l'ordinador de qui
el mira. Les taules no es llegeixen des de cap ruta pública, exportació ni corpus (test `test_snrt_visor_privat.py`). La càrrega la fa
un administrador amb `tools/snrt/puja_al_visor_privat.py`. La pàgina no passa pel cau fora de línia de l'app.

## Conseqüències
- Hi ha text de la SNRT a la base de dades de producció. Només hi arriba qui és administrador; qui administra la biblioteca (`ADMIN_EMAILS`)
  és, per tant, qui controla l'accés: convé mantenir-la curta.
- L'app té el registre obert, però ningú no és administrador si no ho decideix un administrador (`/admin/users/{id}/admin`).
- Cal tenir per escrit el permís de la SNRT per a aquest ús (és una demostració a la mateixa SNRT; pendent del correu de `PERMISOS.md`).
- Si la SNRT demana que s'esborri, es fa amb un `DELETE` de les dues taules.
