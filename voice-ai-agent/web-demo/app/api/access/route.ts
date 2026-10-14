import { NextRequest, NextResponse } from 'next/server';
import {
  ACCESS_COOKIE,
  ACCESS_TTL_SECONDS,
  createAccessCookieValue,
  hasValidAccessCookie,
  verifyAccessCode,
} from '@/lib/demo-access';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  return NextResponse.json(
    { authenticated: hasValidAccessCookie(request) },
    { headers: { 'Cache-Control': 'no-store' } }
  );
}

export async function POST(request: NextRequest) {
  if (!process.env.DEMO_ACCESS_CODE || !process.env.DEMO_SESSION_SECRET) {
    return NextResponse.json(
      { error: 'Demo access is not configured.' },
      { status: 503, headers: { 'Cache-Control': 'no-store' } }
    );
  }

  let code: unknown;
  try {
    code = (await request.json())?.code;
  } catch {
    return NextResponse.json(
      { error: 'Enter the access code to continue.' },
      { status: 400, headers: { 'Cache-Control': 'no-store' } }
    );
  }

  if (!verifyAccessCode(code)) {
    return NextResponse.json(
      { error: 'That access code is not correct.' },
      { status: 401, headers: { 'Cache-Control': 'no-store' } }
    );
  }

  let cookieValue: string;
  try {
    cookieValue = createAccessCookieValue();
  } catch {
    return NextResponse.json(
      { error: 'Demo access is not configured.' },
      { status: 503, headers: { 'Cache-Control': 'no-store' } }
    );
  }

  const response = NextResponse.json(
    { authenticated: true },
    { headers: { 'Cache-Control': 'no-store' } }
  );
  response.cookies.set(ACCESS_COOKIE, cookieValue, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict',
    path: '/api',
    maxAge: ACCESS_TTL_SECONDS,
  });
  return response;
}
