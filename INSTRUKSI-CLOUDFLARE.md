# INSTRUKSI CLOUDFLARE — jasasewapbn/esperasupplements

## 1. Push kerangka ini ke repo baru (sekali saja)

Repo `https://github.com/jasasewapbn/esperasupplements` saat ini **kosong**.
Dari folder project di laptop:

```bash
git remote remove origin
git remote add origin https://github.com/jasasewapbn/esperasupplements.git
git add -A
git commit -m "EsperaSupplements: kerangka autoblog Tenku-like"
git branch -M main
git push -u origin main
```

Login via browser (`gh auth login`) saat diminta. Jangan taruh token di URL.

## 2. Isi Secrets autoblog (wajib agar update 5-jam-an jalan)

Repo GitHub > Settings > Secrets and variables > Actions > New repository secret:

| Secret | Dari mana |
|---|---|
| `DEEPSEEK_API_KEY` | platform.deepseek.com > API keys (butuh balance, 402 = habis) |
| `UNSPLASH_ACCESS_KEY` | unsplash.com/developers > New Application (gratis 50 req/jam) |

Tes: Actions > Autoblog EsperaSupplements > Run workflow > Run → hijau →
commit "Autoblog: artikel baru" muncul di Code.

Jadwal otomatis: `0 */5 * * *` = tiap 5 jam (00/05/10/15/20 UTC).

## 3. Sambungkan ke Cloudflare (otomatisasi deploy)

**Opsi A — Worker Connect to Git (disarankan):**
1. dash.cloudflare.com > Workers & Pages > Create > Worker > Connect to Git.
2. Pilih repo `esperasupplements`, branch `main`.
3. Build: Deploy command `npx wrangler deploy`, Root `/`, Build command kosong.
4. Deploy → dapat URL `*.workers.dev`. Setiap push `main` = tayang ulang ±2 menit.

**Opsi B — Pages Connect to Git:**
1. Workers & Pages > Create > Pages > Connect to Git > pilih repo.
2. Framework: None, Build command kosong, output `/`.
3. Sama-sama otomatis tiap push.

## 4. Pasang domain sendiri (opsional)

1. Pastikan domain nameserver-nya ke Cloudflare (status Active).
2. Worker/Pages > Custom domains > tambah domain > Activate (jangan A-record manual).
3. Tunggu 1–5 menit, buka `https://domainmu` (gembok hijau = beres).
4. Ganti domain di `sitemap.xml` + `robots.txt` + email di `kontak.html`, commit, push.
5. SSL/TLS > aktifkan Always Use HTTPS.

## 5. Troubleshooting

| Gejala | Solusi |
|---|---|
| Actions merah 402 | Saldo DeepSeek habis → top up |
| Actions merah 401/403 Unsplash | Access Key salah / rate limit → cek dashboard Unsplash |
| Hijau tapi tanpa commit | Slug sudah ada atau artikel <350 kata → cek log run |
| Situs tidak berubah setelah push | Build belum Success → cek Deployments, Promote versi terbaru 100% |
| Gambar tidak muncul | `UNSPLASH_ACCESS_KEY` kosong saat run → artikel tanpa foto (normal), run berikutnya coba lagi |
| CSS tidak load | Pastikan link `/styles.css` dan deploy root `/` |

## Checklist

- [ ] Push awal ke `jasasewapbn/esperasupplements` sukses
- [ ] 2 Secrets terisi, Run workflow manual hijau + ada commit artikel
- [ ] URL Cloudflare tampil (Latest/Trending terisi 1 artikel contoh)
- [ ] (Opsional) custom domain + gembok hijau + sitemap diganti
- [ ] Tunggu 5 jam, pastikan run terjadwal hijau sendiri
