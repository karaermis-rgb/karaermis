"""Google Cloud Text-to-Speech ile cümle cümle seslendirme üretir -> ses/vo/NN.mp3

Anahtar, oturumun ağ vekili tarafından istek başlığına eklenir; bu yüzden betik
anahtarı kendisi okumaz. Yerel kullanımda GOOGLE_TTS_KEY ortam değişkeni verilebilir.

  python3 tts.py --voices          # kullanılabilir tr-TR seslerini listele
  python3 tts.py [--voice ADI]     # tüm cümleleri seslendir
"""
import argparse
import base64
import json
import os
import urllib.request

import timeline as T

API = "https://texttospeech.googleapis.com/v1"
PREF = ("Chirp3-HD", "Neural2", "Wavenet", "Standard")


def call(path, body=None):
    req = urllib.request.Request(API + path, method="POST" if body else "GET",
                                 data=json.dumps(body).encode() if body else None)
    req.add_header("Content-Type", "application/json")
    key = os.environ.get("GOOGLE_TTS_KEY", "placeholder")
    req.add_header("X-Goog-Api-Key", key)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def tr_voices():
    v = call("/voices?languageCode=tr-TR")["voices"]
    return sorted((x["name"] for x in v),
                  key=lambda n: next((i for i, p in enumerate(PREF) if p in n), 9))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voices", action="store_true")
    ap.add_argument("--voice")
    ap.add_argument("--rate", type=float, default=0.97)
    a = ap.parse_args()
    if a.voices:
        print("\n".join(tr_voices()))
        return
    voice = a.voice or tr_voices()[0]
    os.makedirs(T.VO_DIR, exist_ok=True)
    print("Ses:", voice)
    for i, text in T.LINES.items():
        if "[BOŞLUK" in text:
            print(f"  {i:02d} atlandı (BOŞLUK)")
            continue
        cfg = {"audioEncoding": "MP3", "sampleRateHertz": 48000}
        if "Chirp" not in voice:
            cfg["speakingRate"] = a.rate
        r = call("/text:synthesize", {"input": {"text": text},
                                      "voice": {"languageCode": "tr-TR", "name": voice},
                                      "audioConfig": cfg})
        with open(T.vo_path(i), "wb") as f:
            f.write(base64.b64decode(r["audioContent"]))
        print(f"  {i:02d} tamam")


if __name__ == "__main__":
    main()
