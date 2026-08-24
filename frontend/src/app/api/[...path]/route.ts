import { type NextRequest, NextResponse } from 'next/server';

// Proxy every /api/* request to the FastAPI backend, resolved at REQUEST time.
//
// This is a Route Handler rather than a next.config `rewrites()` entry on
// purpose: Next.js evaluates rewrites at BUILD time and bakes their
// destination into the compiled routes manifest, so a destination built from
// `process.env.API_INTERNAL_URL` would capture the build-time value (nothing,
// -> localhost) and ignore the real runtime env inside the container. A
// handler reads process.env per request, and also forwards Set-Cookie headers
// reliably (which the browser needs for the auth cookies).

export const dynamic = 'force-dynamic';

const API_BASE = process.env.API_INTERNAL_URL ?? 'http://localhost:8000';

// Headers that must not be copied verbatim between hops.
const STRIP_RESPONSE_HEADERS = new Set([
  'connection',
  'keep-alive',
  'transfer-encoding',
  'content-encoding',
  'content-length',
  'set-cookie', // forwarded separately so multiple cookies aren't collapsed
]);

async function proxy(req: NextRequest, path: string[]): Promise<Response> {
  const target = `${API_BASE}/api/${path.join('/')}${req.nextUrl.search}`;

  const forwardHeaders = new Headers(req.headers);
  forwardHeaders.delete('host');

  const init: RequestInit = {
    method: req.method,
    headers: forwardHeaders,
    redirect: 'manual',
    // Propagate client disconnects (important for the SSE streams) so the
    // upstream request is aborted instead of leaking.
    signal: req.signal,
  };
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    const body = await req.arrayBuffer();
    if (body.byteLength > 0) init.body = body;
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, init);
  } catch {
    return NextResponse.json({ detail: 'Backend unavailable' }, { status: 502 });
  }

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!STRIP_RESPONSE_HEADERS.has(key.toLowerCase())) {
      responseHeaders.set(key, value);
    }
  });

  const res = new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });

  // Forward each Set-Cookie header individually — a Headers object collapses
  // multiple Set-Cookie values into one comma-joined string, which corrupts
  // cookies. `getSetCookie()` (undici / Node 18.14+) returns them as an array.
  const getSetCookie = (
    upstream.headers as unknown as { getSetCookie?: () => string[] }
  ).getSetCookie;
  if (typeof getSetCookie === 'function') {
    for (const cookie of getSetCookie.call(upstream.headers)) {
      res.headers.append('set-cookie', cookie);
    }
  }

  return res;
}

export function GET(req: NextRequest, ctx: { params: { path: string[] } }) {
  return proxy(req, ctx.params.path);
}
export function POST(req: NextRequest, ctx: { params: { path: string[] } }) {
  return proxy(req, ctx.params.path);
}
export function PATCH(req: NextRequest, ctx: { params: { path: string[] } }) {
  return proxy(req, ctx.params.path);
}
export function PUT(req: NextRequest, ctx: { params: { path: string[] } }) {
  return proxy(req, ctx.params.path);
}
export function DELETE(req: NextRequest, ctx: { params: { path: string[] } }) {
  return proxy(req, ctx.params.path);
}
