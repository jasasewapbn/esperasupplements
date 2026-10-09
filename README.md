# EsperaSupplements — Autoblog Suplemen (DeepSeek + Unsplash + Cloudflare)

Blog otomatis berbahasa Indonesia tentang suplemen & nutrisi: artikel ditulis AI
(DeepSeek, 500–700 kata), berfoto otomatis (Unsplash), terbit otomatis tiap
**5 jam** ke **Cloudflare Workers/Pages** dari repo
`jasasewapbn/esperasupplements`.

## Cara kerja

```
Judul di content/antrean-judul.txt (format "Kategori | Judul")
  → GitHub Actions tiap 5 jam (cron "0 */5 * * *") + tombol Run workflow
  → DeepSeek API menulis artikel → Unsplash API mengunduh foto
  → commit "Autoblog: artikel baru" ke branch main
  → Cloudflare build ulang otomatis → tayang ±2 menit
```

Menulis manual juga bisa lewat `/admin/` (token GitHub + key Unsplash via browser saja).

## Fitur & layout

- Layout ala **Tenku** (majalah minimal): topbar sosial, logo tengah, nav kategori,
  section **Latest** (1 besar + 4 kecil), **Trending** (nomor 01–04),
  blok per kategori, **Archives** + **Newsletter**, footer 4 kolom.
- Kategori: Vitamin, Protein, Herbal, Fitness, Diet, Kesehatan.
- Arsip `/blog/` dengan filter `?cat=` dan pencarian `?s=`.
- Halaman: Tentang (panjang), Kontak, ToS, Privasi, DMCA, 404, sitemap, robots.
- Foto otomatis + kredit fotografer Unsplash (sesuai lisensi).

## Struktur repo

```
index.html                 Beranda ala Tenku (Latest/Trending/Archives)
blog/index.html            Arsip + filter + pencarian
blog/post.html             Template artikel (baca .md + render)
tentang.html kontak.html tos.html privasi.html dmca.html 404.html
styles.css                 Tema (termasuk .tk-* Tenku-like, orisinal)
admin/index.html           Editor Git-based (Unsplash)
content/posts/*.md         Artikel Markdown + frontmatter
content/images/*.jpg       Foto Unsplash per artikel
content/index.json         Indeks artikel
content/antrean-judul.txt  Antrean judul (120 topik suplemen)
scripts/autoblog.py        Generator (DeepSeek + Unsplash)
src/worker.js              Cloudflare Worker statis
wrangler.toml              Konfigurasi Worker
.github/workflows/autoblog.yml  Jadwal tiap 5 jam + manual
```

## Setup dari nol (repo baru)

1. **Repo GitHub**: repo `jasasewapbn/esperasupplements` sudah ada (kosong).
   Dari folder ini:
   ```bash
   git remote remove origin
   git remote add origin https://github.com/jasasewapbn/esperasupplements.git
   git add -A && git commit -m "EsperaSupplements: kerangka autoblog Tenku-like" && git push -u origin main
   ```
2. **Secrets GitHub** (repo > Settings > Secrets and variables > Actions > New secret):
   - `DEEPSEEK_API_KEY` — dari platform.deepseek.com (butuh balance).
   - `UNSPLASH_ACCESS_KEY` — dari unsplash.com/developers (gratis).
   - Jangan paste key di chat/file.
3. **Tes autoblog**: Actions > Autoblog EsperaSupplements > Run workflow → hijau →
   commit "Autoblog: artikel baru" muncul → lanjut setup Cloudflare.
4. **Cloudflare Worker** (disarankan, 1 project saja):
   Workers & Pages > Create > Worker > Connect to Git > pilih repo
   `esperasupplements`, branch `main`, deploy command `npx wrangler deploy`, root `/`.
   Dapat URL `https://esperasupplements.workers.dev` (atau pages.dev).
5. **Domain sendiri** (opsional): Worker > Custom domains > tambah domainmu
   (pastikan nameserver ke Cloudflare) → ganti domain di `sitemap.xml` + `robots.txt`.
6. **Jadwal**: otomatis tiap 5 jam (00, 05, 10, 15, 20 UTC ≈ 07, 12, 17, 22, 03 WIB).
   Manual: Actions > Run workflow, isi judul/kategori atau kosongkan (antrean).
   Bila antrean habis, skrip pakai judul cadangan agar tidak gagal.

## Update tiap 5 jam — cek

- Actions > tab runs harus hijau tiap ~5 jam.
- Tiap run menulis 1 file `content/posts/*.md` + 1 foto + update `index.json`.
- Jika 402 DeepSeek = saldo habis → top up. Jika 403 Unsplash = key salah/limit → cek dashboard Unsplash.

## Keamanan

- Semua key hanya via Secrets/Env, tidak di-hardcode.
- Token admin hanya di `localStorage` browser, tidak masuk repo.
