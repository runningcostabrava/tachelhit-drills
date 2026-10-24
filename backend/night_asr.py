"""El transcriptor de nit: proposa el text de les gravacions que ningú no ha escrit.

La biblioteca té gravacions sense text —les nostres que ningú no ha transcrit, i les que entren
de corpus de fora, que porten veu i significat però cap paraula amaziga escrita. Fins ara,
perquè una d'aquelles es tornés una frase calia que una persona s'hi assegués, escoltés i
escrivís. Això és car i és el coll d'ampolla de tot el projecte.

El que fa això: de nit, mentre no hi ha ningú, passa les gravacions pel nostre transcriptor i
desa el que diu **com a proposta**. Al matí, qui parla la llengua no ha d'escriure: ha de dir sí
o no, que és una feina d'un segon.

TRES REGLES QUE NO ES TOQUEN

1. El que surt de la màquina NO és el text del parlant. Va a `text_tachelhit_suggested`, i
   `text_tachelhit` es queda buit fins que una persona ho confirma. És la mateixa regla que ja
   regeix a tot arreu i aquí és tota la raó de ser del camp.
2. Es desa la CERTESA que el model diu que té (`suggested_confidence`, de 0 a 1). Sense això la
   cua és un sac on la frase neta i la inintel·ligible pesen igual; amb això es confirma primer
   el que té més números de ser bo.
3. Una d'una. El Space és una sola CPU i atén d'una en una: demanar-li dues coses alhora no va
   més de pressa, va pitjor.
"""
from __future__ import annotations

import os
import threading
from datetime import datetime
from typing import Dict, Optional

import requests

SPACE_DEFAULT = "https://josepabloucr-huggingface-asr-space.hf.space"

#: Quant s'espera una sola transcripció. El Space adormit triga un minut llarg a despertar-se.
TIMEOUT = 420

_state: Dict[str, object] = {"running": False, "done": 0, "written": 0, "failed": 0,
                             "last": None, "started": None}
_lock = threading.Lock()


def state() -> dict:
    return dict(_state)


def _space() -> str:
    url = os.getenv("HUGGINGFACE_ASR_SPACE_URL", SPACE_DEFAULT).strip()
    if "huggingface.co/spaces/" in url:
        owner, name = url.rsplit("/", 2)[-2:]
        return f"https://{owner}-{name}".replace("_", "-").lower() + ".hf.space"
    return url.rstrip("/")


def transcribe_one(audio_url: str) -> Optional[dict]:
    """El que el transcriptor diu d'una gravació: text, certesa i temps de cada paraula.

    Best effort a posta: una gravació que no es pot transcriure és una gravació que es queda
    esperant, no un error que ningú hagi de veure.
    """
    if not (audio_url or "").strip():
        return None
    token = os.getenv("HUGGINGFACE_API_KEY", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        got = requests.get(audio_url, timeout=120)
        got.raise_for_status()
        resp = requests.post(f"{_space()}/transcribe", headers=headers,
                             files={"audio_file": ("clip", got.content, "application/octet-stream")},
                             timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        out = resp.json() or {}
    except Exception:
        return None
    text = (out.get("text") or "").strip()
    if not text:
        return None
    conf = out.get("confidence")
    try:
        conf = float(conf) if conf is not None else None
    except (TypeError, ValueError):
        conf = None
    return {"text": text, "confidence": conf, "segments": out.get("segments") or []}


def _pending(db, limit: int, redo: bool):
    """Les que esperen: tenen veu i no tenen text amazic.

    Les més curtes primer. Una gravació de dos segons es transcriu bé, es confirma de pressa i
    ensenya si el circuit funciona; una de dos minuts es menja la nit i ningú no la confirma.
    """
    from sqlalchemy import func

    from models import Drill as DrillModel
    q = db.query(DrillModel).filter(
        DrillModel.audio_url.isnot(None), DrillModel.audio_url != "",
        (DrillModel.text_tachelhit.is_(None)) | (DrillModel.text_tachelhit == ""))
    if not redo:
        q = q.filter((DrillModel.text_tachelhit_suggested.is_(None))
                     | (DrillModel.text_tachelhit_suggested == ""))
    return q.order_by(func.length(func.coalesce(DrillModel.text_arabic, "")).asc(),
                      DrillModel.id.desc()).limit(max(1, min(limit, 500))).all()


def _work(session_factory, limit: int, redo: bool):
    db = session_factory()
    try:
        files = _pending(db, limit, redo)
        _state.update({"running": True, "done": 0, "written": 0, "failed": 0,
                       "started": datetime.utcnow().isoformat() + "Z",
                       "last": f"{len(files)} gravacions per transcriure"})
        for d in files:
            got = transcribe_one(d.audio_url)
            _state["done"] = int(_state["done"]) + 1
            if not got:
                _state["failed"] = int(_state["failed"]) + 1
                continue
            d.text_tachelhit_suggested = got["text"]
            if got["confidence"] is not None and hasattr(d, "suggested_confidence"):
                d.suggested_confidence = got["confidence"]
            db.commit()
            _state["written"] = int(_state["written"]) + 1
            _state["last"] = f"{d.id}: {got['text'][:60]}"
    finally:
        _state["running"] = False
        db.close()


def run(session_factory, limit: int = 50, redo: bool = False) -> dict:
    """Engega la tanda en un fil. Si ja n'hi ha una de corrent, no en comença una altra."""
    with _lock:
        if _state.get("running"):
            return state()
        t = threading.Thread(target=_work, args=(session_factory, limit, redo), daemon=True)
        t.start()
    return state()
