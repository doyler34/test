const apiInternalUrl = process.env.API_INTERNAL_URL ?? 'http://localhost:8000';

/** @type {import("next").NextConfig} */
const config = {
  reactStrictMode: true,
  output: 'standalone',
  images: {
    unoptimized: true,
  },
  async rewrites() {
    // The browser only ever talks to this Next.js origin. Proxying /api here
    // (instead of calling the FastAPI backend directly from the browser)
    // keeps auth cookies same-origin — no CORS, no SameSite=None/HTTPS
    // requirement for local or single-VPS deployments.
    return [{ source: '/api/:path*', destination: `${apiInternalUrl}/api/:path*` }];
  },
};

export default config;
