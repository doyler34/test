/** @type {import("next").NextConfig} */
const config = {
  reactStrictMode: true,
  output: 'standalone',
  images: {
    unoptimized: true,
  },
  // NOTE: /api/* is proxied to the backend by the Route Handler at
  // src/app/api/[...path]/route.ts, NOT by a rewrite here. Rewrites bake their
  // destination in at build time, which would ignore the runtime
  // API_INTERNAL_URL and wrongly target build-time localhost.
};

export default config;
