export default {
  async fetch(request, env) {
    // Blog statis — semua file disajikan dari ASSETS.
    // Tidak ada API key di sini. Autoblog jalan di GitHub Actions (DeepSeek + Unsplash),
    // hasilnya di-commit ke repo lalu Worker menayangkan ulang otomatis.
    return env.ASSETS.fetch(request);
  }
};
