#!/usr/bin/env python3
"""Autoblog ternak: generate 1 artikel Bahasa Indonesia via DeepSeek + foto Unsplash.

Pakai:
  DEEPSEEK_API_KEY=xxx UNSPLASH_ACCESS_KEY=yyy python3 scripts/autoblog.py --judul "Judul" --kategori Ayam
  DEEPSEEK_API_KEY=xxx UNSPLASH_ACCESS_KEY=yyy python3 scripts/autoblog.py   # ambil antrean teratas
  python3 scripts/autoblog.py --dry-run --judul "Contoh"                     # test tanpa API

Key HANYA lewat environment variable / GitHub Secrets, jangan di-hardcode.
Secrets yang dibutuhkan di GitHub Actions:
  - DEEPSEEK_API_KEY     (https://platform.deepseek.com)
  - UNSPLASH_ACCESS_KEY  (https://unsplash.com/developers, free 50 req/jam)

Alur: antrean content/antrean-judul.txt (format "Kategori | Judul")
  -> DeepSeek tulis artikel min. 300 kata (cara + modal + estimasi untung)
  -> Unsplash unduh foto landscape
  -> tulis content/posts/<slug>.md + update content/index.json
  -> hapus baris antrean teratas (hanya jika sukses)
"""
import argparse, json, os, re, sys, urllib.request, urllib.parse
from datetime import date

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

UNSPLASH_SEARCH = "https://api.unsplash.com/search/photos"
KATEGORI_QUERY = {
    "Ayam": "chicken poultry farm",
    "Kambing": "goat farm",
    "Sapi": "cow cattle farm",
    "Ikan": "fish farm pond",
    "Pakan": "grain animal feed agriculture",
    "Bisnis": "livestock farm",
}
KATEGORI_VALID = list(KATEGORI_QUERY.keys())

STOPWORDS = {"yang", "dan", "untuk", "dengan", "dari", "pada", "agar", "atau",
             "adalah", "ini", "itu", "dalam", "tiap", "lebih", "tanpa", "serta",
             "sebagai", "oleh", "hingga", "cara", "tips", "panduan", "supaya",
             "berapa", "jenis", "manfaat", "bisnis", "ternak"}


def buat_tags(judul, kategori, maks=5):
    """Tag otomatis: kategori + kata penting dari judul. Kembalikan list."""
    tags = []
    kl = kategori.lower()
    for w in re.findall(r"[a-zA-Z]{4,}", judul.lower()):
        if w in STOPWORDS or w in tags or w == kl:
            continue
        tags.append(w)
        if len(tags) >= maks - 1:
            break
    return [kategori.lower()] + tags

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(REPO_DIR, "content", "antrean-judul.txt")
POSTS = os.path.join(REPO_DIR, "content", "posts")
INDEX = os.path.join(REPO_DIR, "content", "index.json")

SYSTEM = (
    "Kamu penulis blog bisnis ternak Indonesia. Tulis artikel ORISINAL Bahasa Indonesia "
    "yang praktis, membumi, dan jujur soal uang. WAJIB minimal 300 KATA. "
    "Struktur: 3-4 subjudul markdown (##) yang mencakup: cara memulai atau langkah beternak, "
    "rincian modal (contoh angka rupiah: bibit, kandang, pakan), estimasi keuntungan per siklus "
    "atau per bulan, serta risiko dan tips agar tidak rugi. Dilarang menjanjikan pasti untung; "
    "pakai estimasi realistis dan ingatkan bahwa harga bibit, pakan, dan jual fluktuatif per daerah "
    "dan per musim. Akhiri dengan disclaimer 1 kalimat: ini edukasi, bukan saran finansial — "
    "sesuaikan dengan kondisi dan harga di daerahmu."
)

JUDUL_CADANGAN = [
    "Ayam | Ternak Ayam Petelur 100 Ekor: Modal, Pakan, dan Untung per Bulan 2026",
    "Kambing | Modal Ternak 5 Ekor Kambing: Rincian Biaya Lengkap",
    "Sapi | Penggemukan Sapi Potong 90 Hari: Modal, Pakan, dan Margin",
    "Ikan | Budidaya Lele Kolam Terpal: Modal 1 Juta Untung Berapa?",
    "Pakan | Maggot BSF: Budidaya dan Harga Jual per Kg 2026",
    "Bisnis | Mulai Ternak dengan Modal 1 Juta: 5 Pilihan Hewan",
]


def slugify(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s).strip()
    return re.sub(r"-+", "-", re.sub(r"\s+", "-", s))[:80] or "artikel"


def hitung_kata(s):
    return len(re.findall(r"\S+", s))


def clean_excerpt(s, limit=200):
    s = re.sub(r"^#+\s*", "", s)
    for ch in ('*', '_', '`', '"'):
        s = s.replace(ch, "")
    return re.sub(r"\s+", " ", s).strip()[:limit].rstrip()


def split_hasil(teks):
    lines = teks.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and lines[0].strip().upper().startswith("RINGKASAN:"):
        ringkas = lines[0].split(":", 1)[1].strip()
        isi = "\n".join(lines[1:]).strip()
        if ringkas:
            return clean_excerpt(ringkas), (isi or teks.strip())
    first = next((l.strip() for l in lines if l.strip()), "")
    return clean_excerpt(first), teks.strip()


def baca_antrean():
    if not os.path.exists(QUEUE):
        return []
    return [l.strip() for l in open(QUEUE, encoding="utf-8") if l.strip()]


def pop_queue():
    lines = baca_antrean()
    if not lines:
        return None, None
    first = lines[0]
    if " | " in first:
        kat, judul = first.split(" | ", 1)
        kat = kat.strip() or "Bisnis"
        if kat not in KATEGORI_VALID:
            kat = "Bisnis"
        return kat, judul.strip()
    return "Bisnis", first


def hapus_kepala(baris_mentah):
    lines = baca_antrean()
    if lines and lines[0] == baris_mentah:
        open(QUEUE, "w", encoding="utf-8").write(
            "\n".join(lines[1:]) + ("\n" if len(lines) > 1 else ""))


def generate(judul, kategori, dry_run):
    if dry_run:
        return (f"RINGKASAN: Panduan praktis {judul} untuk pemula.\n"
                f"## Pengantar\n\nArtikel tentang **{judul}**.\n\n"
                f"## Poin penting\n\n- Poin 1\n- Poin 2\n\n*Draf dry-run.*")
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        sys.exit("ERROR: DEEPSEEK_API_KEY kosong. Set env dulu (jangan taruh di chat/file).")
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": (
                f"Tulis artikel lengkap berjudul: {judul}\nKategori: {kategori}\n"
                "Panjang WAJIB minimal 300 kata. Awali dengan ringkasan 1 kalimat "
                "diawali 'RINGKASAN: ', lalu isi artikel markdown.")},
        ],
        "temperature": 0.8, "max_tokens": 1500,
    }).encode()
    req = urllib.request.Request(API_URL, data=payload,
                                 headers={"Authorization": "Bearer " + key,
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = json.load(r)
    except Exception as e:
        sys.exit(f"ERROR DeepSeek API: {e}")
    try:
        return body["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        sys.exit(f"ERROR respons tak terduga: {str(body)[:200]}")


def ambil_gambar_unsplash(slug, kategori):
    """Unduh 1 foto relevan dari Unsplash. Kembalikan dict atau None.
    Key dari env UNSPLASH_ACCESS_KEY — tidak pernah di-hardcode."""
    key = os.environ.get("UNSPLASH_ACCESS_KEY", "").strip()
    if not key:
        print("INFO: UNSPLASH_ACCESS_KEY kosong — artikel tanpa foto.")
        return None
    try:
        q = KATEGORI_QUERY.get(kategori, "livestock farm")
        url = UNSPLASH_SEARCH + "?" + urllib.parse.urlencode(
            {"query": q, "per_page": 3, "orientation": "landscape",
             "content_filter": "high"})
        req = urllib.request.Request(
            url, headers={"Authorization": f"Client-ID {key}",
                          "Accept-Version": "v1",
                          "User-Agent": "Ternak-Autoblog/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r) or {}
        fotos = data.get("results") or []
        if not fotos:
            print("INFO: Unsplash tidak mengembalikan foto — artikel tanpa foto.")
            return None
        foto = fotos[0]
        urls = foto.get("urls") or {}
        src = urls.get("regular") or urls.get("full") or urls.get("raw")
        if not src:
            return None
        sep = "&" if "?" in src else "?"
        src_dl = f"{src}{sep}w=1200&q=80&fm=jpg"
        dest = os.path.join(REPO_DIR, "content", "images", slug + ".jpg")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        dl = urllib.request.Request(src_dl, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"})
        with urllib.request.urlopen(dl, timeout=60) as fr, open(dest, "wb") as fw:
            fw.write(fr.read())
        user = (foto.get("user") or {})
        nama = user.get("name", "Unsplash")
        user_link = (user.get("links") or {}).get("html", "https://unsplash.com")
        try:
            dl_ep = (foto.get("links") or {}).get("download_location")
            if dl_ep:
                urllib.request.urlopen(urllib.request.Request(
                    dl_ep, headers={"Authorization": f"Client-ID {key}"}), timeout=15).read()
        except Exception:
            pass
        print(f"OK gambar: content/images/{slug}.jpg (oleh {nama})")
        return {"image": f"/content/images/{slug}.jpg",
                "credit": f"Foto oleh {nama} di Unsplash",
                "url": f"{user_link}?utm_source=ternakblog&utm_medium=referral"}
    except Exception as e:
        print(f"INFO: gambar dilewati ({e})")
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judul", default="")
    ap.add_argument("--kategori", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    q_kat, q_judul = pop_queue() if not a.judul.strip() else ("", "")
    judul = a.judul.strip() or q_judul
    kategori = a.kategori.strip() or q_kat or "Bisnis"
    if kategori not in KATEGORI_VALID:
        kategori = "Bisnis"
    dari_antrean = not a.judul.strip() and bool(q_judul)
    baris_mentah = next((l for l in baca_antrean()
                         if l == judul or l.endswith(" | " + judul)), judul) if judul else ""
    if not judul:
        import random
        kat_jud = random.choice(JUDUL_CADANGAN).split(" | ", 1)
        kategori, judul = kat_jud[0], kat_jud[1]
        dari_antrean = False
        baris_mentah = ""
        print(f"INFO: antrean kosong — pakai judul cadangan: {kategori} | {judul}")
    slug = slugify(judul)
    target = os.path.join(POSTS, slug + ".md")
    if os.path.exists(target):
        sys.exit(f"Slug {slug} sudah ada — pilih judul lain.")

    teks = generate(judul, kategori, a.dry_run)
    ringkasan, isi = split_hasil(teks)
    if not a.dry_run and hitung_kata(isi) < 250:
        sys.exit(f"ERROR: artikel terlalu pendek ({hitung_kata(isi)} kata, minimal 250) — "
                 f"tidak diterbitkan agar blog tidak rusak.")

    os.makedirs(POSTS, exist_ok=True)
    gbr = None if a.dry_run else ambil_gambar_unsplash(slug, kategori)
    tags = buat_tags(judul, kategori)
    img_meta = ""
    if gbr:
        img_meta = (f"image: {gbr['image']}\n"
                    f"image_credit: {json.dumps(gbr['credit'], ensure_ascii=False)}\n"
                    f"image_url: {gbr['url']}\n")
    with open(target, "w", encoding="utf-8") as f:
        f.write(f"---\ntitle: {json.dumps(judul)}\ndate: {date.today().isoformat()}\n"
                f"category: {kategori}\nexcerpt: {json.dumps(ringkasan)}\n"
                f"tags: {json.dumps(tags, ensure_ascii=False)}\n{img_meta}---\n\n{isi}\n")

    idx = json.load(open(INDEX, encoding="utf-8")) if os.path.exists(INDEX) else []
    idx = [x for x in idx if x.get("slug") != slug]
    entry = {"slug": slug, "title": judul, "date": date.today().isoformat(),
             "category": kategori, "excerpt": ringkasan, "tags": tags}
    if gbr:
        entry.update({"image": gbr["image"], "image_credit": gbr["credit"], "image_url": gbr["url"]})
    idx.insert(0, entry)
    idx.sort(key=lambda x: x.get("date", ""), reverse=True)
    json.dump(idx, open(INDEX, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if dari_antrean and not a.dry_run and baris_mentah:
        hapus_kepala(baris_mentah)
    print(f"OK: {target} ({hitung_kata(isi)} kata)")


if __name__ == "__main__":
    main()
