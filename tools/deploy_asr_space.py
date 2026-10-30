"""Push huggingface-asr-space/ to the HuggingFace Space that production uses for ASR.

    python tools/deploy_asr_space.py            # upload + print the build state
    python tools/deploy_asr_space.py --status   # just the Space's runtime stage
    python tools/deploy_asr_space.py --logs     # last build/run log lines

Needs HF_TOKEN (write) in backend/.env or the environment. The Space rebuilds on upload;
production's /transcribe calls fail while it builds (~10 min), so deploy when no capture job runs.
"""
import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPACE_DIR = os.path.join(ROOT, "huggingface-asr-space")
SPACE_ID = os.getenv("ASR_SPACE_ID", "josepabloucr/huggingface-asr-space")
ADAPTER_REPO = os.getenv("MMS_ADAPTER_REPO", "josepabloucr/mms-1b-shi-tachelhit")


def token() -> str:
    t = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
    if not t:
        try:
            from dotenv import load_dotenv
            load_dotenv(os.path.join(ROOT, "backend", ".env"))
            t = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
        except ImportError:
            pass
    if not t:
        sys.exit("HF_TOKEN not set (backend/.env or environment)")
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--logs", action="store_true")
    ap.add_argument("--wait", type=int, default=0, help="poll the runtime stage for N minutes after upload")
    a = ap.parse_args()
    from huggingface_hub import HfApi
    api = HfApi(token=token())
    if a.status or a.logs:
        rt = api.get_space_runtime(SPACE_ID)
        print(f"{SPACE_ID}: stage={rt.stage} hardware={rt.hardware}")
        if a.logs:
            import requests
            r = requests.get(f"https://huggingface.co/api/spaces/{SPACE_ID}/logs/build",
                             headers={"Authorization": f"Bearer {token()}"}, timeout=30, stream=True)
            print(r.text[-6000:] if r.ok else f"logs: {r.status_code}")
        return
    # The fine-tuned MMS adapter (8.9 MB) is not in git: it lives in a private model repo and
    # is copied into the Space at deploy time, so the Space needs no secret to read it (#491).
    from huggingface_hub import hf_hub_download
    import shutil
    got = hf_hub_download(ADAPTER_REPO, "adaptador_shi.pt", token=token())
    shutil.copy(got, os.path.join(SPACE_DIR, "adaptador_shi.pt"))
    print(f"uploading {SPACE_DIR} -> {SPACE_ID}")
    api.upload_folder(folder_path=SPACE_DIR, repo_id=SPACE_ID, repo_type="space",
                      ignore_patterns=["__pycache__/*", "*.pyc", ".DS_Store"],
                      commit_message="NeMo (/transcribe, /align) + MMS-1b-all with our shi adapter (/transcribe_mms)")
    print("uploaded; the Space is rebuilding")
    deadline = time.time() + a.wait * 60
    last = None
    while time.time() < deadline:
        st = api.get_space_runtime(SPACE_ID).stage
        if st != last:
            print(time.strftime("%H:%M:%S"), st, flush=True); last = st
        if st in ("RUNNING", "BUILD_ERROR", "RUNTIME_ERROR"):
            break
        time.sleep(20)


if __name__ == "__main__":
    main()
