import { createHmac, randomUUID, timingSafeEqual } from 'node:crypto';

export const ACCESS_COOKIE = 'superkalam_demo_access';
export const ACCESS_TTL_SECONDS = 15 * 60;

function safeEqual(left: string, right: string): boolean {
  const a = Buffer.from(left);
  const b = Buffer.from(right);
  return a.length === b.length && timingSafeEqual(a, b);
}

export function verifyAccessCode(code: unknown): boolean {
  const expected = process.env.DEMO_ACCESS_CODE;
  return typeof code === 'string' && Boolean(expected) && safeEqual(code, expected!);
}

export function createAccessCookieValue(): string {
  const secret = process.env.DEMO_SESSION_SECRET;
  if (!secret || secret.length < 32) {
    throw new Error('DEMO_SESSION_SECRET must contain at least 32 characters');
  }
  const nonce = randomUUID();
  const signature = createHmac('sha256', secret).update(nonce).digest('base64url');
  return `${nonce}.${signature}`;
}

export function verifyAccessCookie(value: string | undefined): boolean {
  const secret = process.env.DEMO_SESSION_SECRET;
  if (!value || !secret || secret.length < 32) return false;
  const [nonce, signature, extra] = value.split('.');
  if (!nonce || !signature || extra) return false;
  const expected = createHmac('sha256', secret).update(nonce).digest('base64url');
  return safeEqual(signature, expected);
}

export function hasValidAccessCookie(request: Request): boolean {
  const cookie = request.headers
    .get('cookie')
    ?.split(';')
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${ACCESS_COOKIE}=`))
    ?.slice(ACCESS_COOKIE.length + 1);
  try {
    return verifyAccessCookie(cookie ? decodeURIComponent(cookie) : undefined);
  } catch {
    return false;
  }
}
