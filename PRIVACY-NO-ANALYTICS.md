# AgentenIndex — Cloudflare Web Analytics removed

Updated: 2026-09-29

- Removed the Cloudflare Web Analytics JavaScript beacon from all HTML pages.
- Removed references to static.cloudflareinsights.com/beacon.min.js and the site analytics token.
- Cloudflare DNS, proxy, TLS and security configuration are not affected by this source-code change.
- No Google Analytics, Microsoft Clarity, Meta Pixel or other marketing/analytics tracker was added.
- Agenten-Check remains a separate deployment and contains no Cloudflare Web Analytics beacon in the privacy-hardened build.
