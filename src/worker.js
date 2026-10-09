export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = url.origin;
    const xmlHead = '<?xml version="1.0" encoding="UTF-8"?>\n';
    const xmlHeaders = {
      'Content-Type': 'application/xml; charset=utf-8',
      'Cache-Control': 'public, max-age=3600',
    };

    // robots.txt dinamis — Sitemap selalu ikut domain yang diakses
    if (url.pathname === '/robots.txt') {
      return new Response(
        `User-agent: *\nAllow: /\nSitemap: ${origin}/sitemap.xml\n`,
        { headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'public, max-age=3600' } }
      );
    }

    // sitemap.xml (index) dinamis
    if (url.pathname === '/sitemap.xml') {
      const xml = xmlHead +
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        `  <sitemap><loc>${origin}/sitemap-pages.xml</loc></sitemap>\n` +
        `  <sitemap><loc>${origin}/content/sitemap-posts.xml</loc></sitemap>\n` +
        '</sitemapindex>\n';
      return new Response(xml, { headers: xmlHeaders });
    }

    // sitemap halaman statis — dinamis
    if (url.pathname === '/sitemap-pages.xml') {
      const pages = [
        ['/', 'daily', '1.0'], ['/blog/', 'daily', '0.9'],
        ['/tentang.html', 'monthly', '0.5'], ['/kontak.html', 'monthly', '0.5'],
        ['/tos.html', 'yearly', '0.3'], ['/privasi.html', 'yearly', '0.3'],
        ['/dmca.html', 'yearly', '0.3'],
      ];
      const body = pages.map(([p, f, pr]) =>
        `  <url><loc>${origin}${p}</loc><changefreq>${f}</changefreq><priority>${pr}</priority></url>`
      ).join('\n');
      return new Response(xmlHead +
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        body + '\n</urlset>\n', { headers: xmlHeaders });
    }

    // sitemap artikel — dinamis dari index.json (fallback ke file statis bila gagal)
    if (url.pathname === '/content/sitemap-posts.xml') {
      try {
        const r = await env.ASSETS.fetch(new Request(origin + '/content/index.json'));
        if (!r.ok) throw new Error('index.json ' + r.status);
        const posts = await r.json();
        const body = (Array.isArray(posts) ? posts : [])
          .filter(p => p && p.slug)
          .map(p => `  <url><loc>${origin}/blog/post.html?p=${p.slug}</loc>` +
            `<lastmod>${p.date || new Date().toISOString().slice(0, 10)}</lastmod>` +
            `<changefreq>monthly</changefreq><priority>0.7</priority></url>`)
          .join('\n');
        return new Response(xmlHead +
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
          body + '\n</urlset>\n', { headers: xmlHeaders });
      } catch (e) {
        return env.ASSETS.fetch(request);
      }
    }

    // Selain itu: sajikan file statis blog.
    return env.ASSETS.fetch(request);
  }
};
