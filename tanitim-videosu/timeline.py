"""Senaryo zaman çizelgesi: sahneler, çekimler, kartlar ve altyazılar.

Seslendirme dosyaları (ses/vo/NN.mp3) varsa cümle süreleri onlardan alınır;
yoksa okunma hızından tahmin edilir (taslak).
"""
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
VO_DIR = os.path.join(HERE, "ses", "vo")

SCHOOL = "Şehit Yavuz Sonat Güzel Mesleki ve Teknik Anadolu Lisesi"
FIELD = "Yiyecek İçecek Hizmetleri Alanı"

# Cümleler (altyazı = seslendirme). id -> metin
LINES = {
    1: "Mutfakta bir lezzet doğarken, onun arkasındaki ustayı hiç merak ettin mi?",
    2: "Peki o usta… sen olabilir misin?",
    3: f"{SCHOOL}'nde {FIELD}'na hoş geldin.",
    4: "Burada mesleği kitaptan değil, tezgâhın başında, yaparak öğreniyorsun.",
    5: "Bu alanda mutfak tekniklerinden sunuma kadar, mesleğin her adımını öğreniyorsun.",
    6: "[BOŞLUK – 1. dalın tek cümlelik tanımı]",
    16: "[BOŞLUK – 2. dalın tek cümlelik tanımı]",
    17: "[BOŞLUK – 3. dalın tek cümlelik tanımı]",
    18: "Mutfakta her tabak; bilgi, emek ve yaratıcılığın buluştuğu küçük bir eserdir.",
    19: "Malzemeyi tanımayı, doğru pişirme tekniklerini ve tabağı özenle sunmayı adım adım öğreniyorsun.",
    20: "Disiplin, özen ve yaratıcılık; bu meslekte seni öne çıkaracak üç anahtar.",
    21: "Her uygulamada, her denemede yanında olacaklar.",
    22: "Geleceğini kendi ellerinle hazırla.",
    7: "Uygulamalarımızı [BOŞLUK – atölye adı ve donanımı] ortamında yapıyoruz.",
    8: "Hijyen, mutfak güvenliği ve ekip çalışması, her uygulamanın temelidir.",
    9: "[BOŞLUK – işletmelerde beceri eğitimi / staj bilgisi]",
    10: "Bu alan, yetenekli ellere birçok kapı açar.",
    11: "Restoranlar, oteller, pastaneler, toplu yemek işletmeleri ve kendi işletmen…",
    12: "[BOŞLUK – okulun vermek istediği somut kariyer bilgisi]",
    13: "Bu yolda sana alan öğretmenlerimiz Ebru KARAERMİŞ ve Alpay ŞİMŞEK rehberlik ediyor.",
    14: "Lezzetin peşinden gitmeye hazır mısın?",
    15: "Seni de mutfağımıza bekliyoruz!",
    23: "Soslardan hamur işlerine, tatlılardan sıcak yemeklere; her yeni tarif sana yeni bir beceri kazandırır.",
    24: "Önlüğünü giydiğin an, sınıf bir mutfağa, sen de bir aşçıya dönüşürsün.",
    25: "Çünkü lezzet, her zaman ve her yerde aranan bir değerdir.",
}

# Sahneler: her sahnede cümleler, çekimler (foto yuvası + hareket) ve kartlar.
# move: zoom_in | zoom_out | pan_r | pan_l | parallax
SCENES_169 = [
    dict(name="acilis", lines=[1, 2], pad=2.0, ticks=True,
         shots=[("FOTO-1", "zoom_in"), ("KLIP-1", "video")], cuts=[2],
         cards=[dict(at=0.4, shot=0, kind="question", title="Bu usta sen olabilir misin?")]),
    dict(name="alan", lines=[3, 4, 18], pad=1.5,
         shots=[("FOTO-2", "pan_r"), ("KLIP-2@3.5", "video"), ("FOTO-12", "zoom_in"), ("FOTO-1", "pan_l")],
         cuts=[4, 18, 18.0],
         cards=[dict(at=0.5, shot=0, kind="title", title=FIELD, sub="Kandıra · Kocaeli")]),
    dict(name="ogren", lines=[5, 19, 23], pad=2.5,
         shots=[("FOTO-3", "zoom_in"), ("FOTO-6", "zoom_in"), ("FOTO-4", "zoom_out"),
                ("KLIP-2@5", "video"), ("FOTO-5", "zoom_in")],
         cards=[dict(at=0.0, shot=0, kind="info", title="NE ÖĞRENİYORSUN?", sub="Mutfak Teknikleri"),
                dict(at=0.0, shot=2, kind="info", title="NE ÖĞRENİYORSUN?", sub="Hijyen ve Güvenlik"),
                dict(at=0.0, shot=4, kind="info", title="NE ÖĞRENİYORSUN?", sub="Sunum ve Servis")]),
    dict(name="atolye", lines=[24, 8], pad=2.5, sizzle=True,
         shots=[("KLIP-2@0", "video"), ("FOTO-6", "parallax")],
         cards=[dict(at=0.6, shot=0, kind="label", title="Atölye ve Uygulama")]),
    dict(name="kariyer", lines=[10, 11, 25, 20], pad=2.5, lift=True,
         shots=[("FOTO-9", "zoom_in"), ("KLIP-3@4", "video"), ("KLIP-1@3.5", "video")], cuts=[25, 20],
         cards=[dict(at=0.3, shot=0, kind="list", title="Nerelerde çalışabilirsin?",
                     items=["Restoranlar", "Oteller", "Pastaneler",
                            "Toplu yemek işletmeleri", "Kendi işletmen"])]),
    dict(name="ogretmenler", lines=[13, 21], pad=2.5, calm=True,
         shots=[("FOTO-11", "zoom_out")],
         cards=[dict(at=0.4, kind="names", title="Alan Öğretmenlerimiz",
                     items=["Ebru KARAERMİŞ", "Alpay ŞİMŞEK"])]),
    dict(name="kapanis", lines=[14, 22, 15], pad=1.5,
         shots=[("KLIP-3", "video"), ("FOTO-12", "zoom_out")], cuts=[15],
         cards=[dict(at=0.3, shot=1, kind="cta", title="Seni de mutfağımıza bekliyoruz!")]),
    dict(name="kunye", lines=[], pad=9.0, endcard=True, shots=[], cards=[]),
]

# 60 sn dikey kesit: aynı cümlelerin alt kümesi
SCENES_916 = [
    dict(name="acilis", lines=[1, 2], pad=1.6, ticks=True,
         shots=[("FOTO-1", "zoom_in"), ("KLIP-1", "video")], cuts=[2],
         cards=[dict(at=0.2, shot=0, kind="question", title="Bu usta sen olabilir misin?")]),
    dict(name="alan", lines=[4], pad=1.2,
         shots=[("FOTO-2", "pan_r"), ("KLIP-2@3.5", "video")],
         cards=[dict(at=0.3, shot=0, kind="title", title=FIELD, sub="Kandıra · Kocaeli")]),
    dict(name="ogren", lines=[5, 23], pad=2.5,
         shots=[("FOTO-3", "zoom_in"), ("FOTO-6", "zoom_in"), ("FOTO-4", "zoom_out"),
                ("KLIP-2@5", "video"), ("FOTO-5", "zoom_in")],
         cards=[dict(at=0.0, shot=0, kind="info", title="NE ÖĞRENİYORSUN?", sub="Mutfak Teknikleri"),
                dict(at=0.0, shot=2, kind="info", title="NE ÖĞRENİYORSUN?", sub="Hijyen ve Güvenlik"),
                dict(at=0.0, shot=4, kind="info", title="NE ÖĞRENİYORSUN?", sub="Sunum ve Servis")]),
    dict(name="atolye", lines=[24], pad=1.5, sizzle=True,
         shots=[("KLIP-2@0", "video")],
         cards=[dict(at=0.3, shot=0, kind="label", title="Atölye ve Uygulama")]),
    dict(name="kariyer", lines=[11], pad=3.2, lift=True,
         shots=[("FOTO-9", "zoom_in"), ("KLIP-1@3.5", "video")],
         cards=[dict(at=0.2, shot=0, kind="list", title="Nerelerde çalışabilirsin?",
                     items=["Restoranlar", "Oteller", "Pastaneler",
                            "Toplu yemek", "Kendi işletmen"])]),
    dict(name="kapanis", lines=[15], pad=3.8,
         shots=[("KLIP-3", "video"), ("FOTO-12", "zoom_out")],
         cards=[dict(at=0.2, shot=1, kind="cta", title="Seni de mutfağımıza bekliyoruz!")]),
    dict(name="kunye", lines=[], pad=4.5, endcard=True, shots=[], cards=[]),
]

ENDCARD = dict(
    title=SCHOOL,
    sub=FIELD,
    rows=["Kandıra · Kocaeli"],
)

# ---------------------------------------------------------------- ÖRNEK sürüm
# ORNEK=1 ile çalıştırılırsa eksik bilgiler açıkça ÖRNEK etiketli uydurma
# değerlerle doldurulur. Yayına uygun DEĞİLDİR; yalnızca tam hâlin görünümü için.
ORNEK = os.environ.get("ORNEK") == "1"
if ORNEK:
    LINES.update({
        105: "Okulumuzda Aşçılık, Pastacılık ve Servis dallarında uzmanlaşabilirsin.",
        106: "Aşçılıkta sıcak ve soğuk mutfağın tüm inceliklerini öğrenirsin.",
        116: "Pastacılıkta hamurdan süslemeye, tatlıların dünyasını keşfedersin.",
        117: "Serviste ise misafiri ağırlamanın ve sunumun ustası olursun.",
        107: "Uygulamalarımızı tam donanımlı uygulama mutfağımızda yapıyoruz.",
        109: "Son sınıfta işletmelerde beceri eğitimi alarak meslek hayatına erkenden adım atıyorsun.",
        112: "Mezun olduğunda kendi mutfağını kuracak bilgi ve beceriyle donanmış olursun.",
    })
    _dal = [("Aşçılık", "FOTO-3"), ("Pastacılık", "FOTO-4"), ("Servis", "FOTO-5")]
    _dallar = lambda lines, pad: dict(
        name="dallar", lines=lines, pad=pad, cuts=[116, 117] if 116 in lines else [],
        shots=[(f, "zoom_in" if i % 2 == 0 else "zoom_out") for i, (_, f) in enumerate(_dal)],
        cards=[dict(at=0.0, shot=i, kind="info", title="DAL · ÖRNEK", sub=n, **({"line": l} if l in lines else {}))
               for i, ((n, _), l) in enumerate(zip(_dal, (106, 116, 117)))])
    SCENES_169 = [
        SCENES_169[0], SCENES_169[1],
        _dallar([105, 106, 116, 117], 2.0),
        dict(SCENES_169[2], lines=[5, 19, 23], pad=2.0),
        dict(SCENES_169[3], lines=[107, 24, 8, 109], pad=2.5),
        dict(SCENES_169[4], lines=[10, 11, 112, 20], pad=2.5, cuts=[112, 20]),
        SCENES_169[5], SCENES_169[6], SCENES_169[7],
    ]
    SCENES_916 = [
        SCENES_916[0], SCENES_916[1],
        _dallar([105, 106, 116, 117], 0.8),
        dict(SCENES_916[3], lines=[107], pad=1.5),
        dict(SCENES_916[4], lines=[11], pad=2.0),
        SCENES_916[5],
        dict(SCENES_916[6], pad=2.4),
    ]
    ENDCARD = dict(ENDCARD, rows=[
        "Adres: Örnek Mah. Okul Cad. No:1 Kandıra / Kocaeli (ÖRNEK)",
        "Telefon: 0 (262) 000 00 00 (ÖRNEK)",
        "Web: ornek-okul.meb.k12.tr (ÖRNEK)",
    ])

GAP = 0.35  # cümleler arası sessizlik


def vo_path(i):
    return os.path.join(VO_DIR, f"{i:02d}.mp3")


def line_duration(i):
    p = vo_path(i)
    if os.path.exists(p):
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", p]).decode().strip()
        return float(out)
    return max(1.6, len(LINES[i]) / 13.0 + 0.4)  # tahmini okuma süresi


def build(scenes, target=None):
    """Mutlak zamanlı zaman çizelgesi döndürür."""
    t = 0.0
    out_scenes, subs = [], []
    for sc in scenes:
        start = t
        lt = start + 0.3
        for i in sc["lines"]:
            d = line_duration(i)
            subs.append(dict(id=i, start=lt, end=lt + d, text=LINES[i]))
            lt += d + GAP
        end = max(lt, start + 0.3) + sc["pad"]
        out_scenes.append(dict(sc, start=start, end=end))
        t = end
    total = t
    if target and abs(total - target) > 0.5:
        # pad'leri orantılı ayarla (yalnızca kısa kesit için)
        pass
    return dict(scenes=out_scenes, subs=subs, total=total)


def load_photos():
    with open(os.path.join(HERE, "fotolar.json"), encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    for name, sc in (("16:9", SCENES_169), ("9:16", SCENES_916)):
        tl = build(sc)
        print(name, f"{tl['total']:.1f} sn")
        for s in tl["scenes"]:
            print(f"  {s['name']:12s} {s['start']:6.1f} → {s['end']:6.1f}")
