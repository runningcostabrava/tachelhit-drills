"""Afina el desplacament d'un episodi mut i en diu la prova, marca per marca.

De cada marca nostra es mira si, al segon que prediu el desplacament, el subtitol del video
CANVIA de debo. Es busca el canvi mes gran dins d'una finestra, es pren la mediana de les
diferencies (que es el desplacament afinat) i es compta quantes marques hi cauen a prop.

El numero sol no vol dir res si no se sap que dona l'atzar: per aixo es repeteix tot amb cent
desplacaments triats a l'atzar, i es diu quantes marques hi casen de mitjana. La proporcio entre
les dues xifres es la prova.

US: prova_canvis.py <id_del_video> <episodi> <desplacament>
"""
import sys

import numpy as np

import canvis
import marques

FPS = canvis.FPS
FINESTRA = 2.0   #: segons a banda i banda on es busca el canvi
A_PROP = 0.5     #: es considera que casa si queda a menys d'aixo de la mediana


def deltes(senyal, temps, D):
    """Per cada marca, a quina distancia queda el canvi mes gran de la finestra."""
    w = int(FINESTRA * FPS)
    fora = []
    for t in temps:
        i = int(round((t + D) * FPS))
        a, b = i - w, i + w + 1
        if a < 0 or b > len(senyal):
            continue
        tros = senyal[a:b]
        if tros.max() <= 0:
            continue
        fora.append((a + int(np.argmax(tros))) / FPS - (t + D))
    return np.array(fora)


def mesura(vid, ep, D):
    dif = canvis.canvis_del_video(vid)
    senyal = np.minimum(dif, np.percentile(dif, 97))
    files = marques.carrega()[ep]
    temps = [f[0] for f in files]

    d = deltes(senyal, temps, D)
    mediana = float(np.median(d))
    afinat = D + mediana
    d2 = deltes(senyal, temps, afinat)
    casen = int((np.abs(d2) <= A_PROP).sum())
    dispersio = float(np.std(d2[np.abs(d2) <= A_PROP])) if casen else 0.0

    #: El mateix amb els altres desplacaments possibles, per saber que dona la casualitat.
    #: ATENCIO: el refinat enganxa al bo qualsevol desplacament que ja hi caigui a prop, i
    #: llavors el comptaria com un encert de l'atzar. Per aixo nomes valen els que acaben
    #: en un ALTRE lloc. I el marge es estret: l'episodi gairebe omple el video.
    marge = len(senyal) / FPS - temps[-1]
    baix, alt = -temps[0], marge
    print(f"  (desplaçaments possibles: de {baix:.0f} a {alt:.0f} s, "
          f"només {alt-baix:.0f} s de marge)")
    atzar = []
    for r in np.arange(baix, alt, 0.25):
        da = deltes(senyal, temps, float(r))
        if not len(da):
            continue
        rr = float(r) + float(np.median(da))
        if abs(rr - afinat) <= 1.0:
            continue
        atzar.append(int((np.abs(deltes(senyal, temps, rr)) <= A_PROP).sum()))
    atzar = np.array(atzar or [0])

    print(f"episodi {ep} · vídeo {vid}")
    print(f"  desplaçament afinat: {afinat:.2f} s  (de partida {D})")
    print(f"  marques: {len(temps)}  ·  amb canvi de subtítol a menys de {A_PROP}s: {casen} "
          f"({100*casen/len(temps):.0f}%)")
    print(f"  dispersió de les que casen: {dispersio:.3f} s")
    print(f"  a l'atzar en casarien {atzar.mean():.0f} ± {atzar.std():.0f} "
          f"(el màxim de tots: {atzar.max()})")
    quants_sigma = (casen - atzar.mean()) / (atzar.std() or 1)
    print(f"  o sigui {quants_sigma:.0f} desviacions per damunt de la casualitat")
    return {"desplacament": round(afinat, 2), "marques": len(temps), "casen": casen,
            "dispersio": round(dispersio, 3), "atzar_mitjana": round(float(atzar.mean()), 1),
            "atzar_maxim": int(atzar.max()), "sigmes": round(float(quants_sigma), 1)}


if __name__ == "__main__":
    mesura(sys.argv[1], int(sys.argv[2]), float(sys.argv[3]))
