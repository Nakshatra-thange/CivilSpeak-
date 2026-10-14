'use client';

import { FormEvent, useEffect, useState } from 'react';

export function AccessGate() {
  const [authenticated, setAuthenticated] = useState(false);
  const [checking, setChecking] = useState(true);
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetch('/api/access', { cache: 'no-store' })
      .then((response) => response.json())
      .then((data) => setAuthenticated(data.authenticated === true))
      .catch(() => setError('Could not check demo access. Please try again.'))
      .finally(() => setChecking(false));
  }, []);

  async function submitCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const response = await fetch('/api/access', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Access could not be verified.');
      setAuthenticated(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Access could not be verified.');
    } finally {
      setSubmitting(false);
    }
  }

  if (authenticated) return null;

  return (
    <div className="bg-background/95 fixed inset-0 z-[100] grid place-items-center px-5 py-8 backdrop-blur">
      <section className="bg-card w-full max-w-lg rounded-2xl border p-6 shadow-xl sm:p-8">
        <p className="text-muted-foreground font-mono text-xs tracking-widest uppercase">
          SuperKalam · Voice Mock
        </p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight">Enter the demo access code</h1>
        <p className="text-muted-foreground mt-2 text-sm leading-6">
          This private preview runs a live voice interview. The connection ends after 15 minutes.
        </p>

        <form className="mt-6 space-y-3" onSubmit={submitCode}>
          <label className="sr-only" htmlFor="demo-access-code">
            Access code
          </label>
          <input
            id="demo-access-code"
            autoComplete="off"
            required
            type="password"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            placeholder="Access code"
            className="bg-background focus-visible:ring-ring w-full rounded-lg border px-4 py-3 text-sm outline-none focus-visible:ring-2"
          />
          <button
            type="submit"
            disabled={checking || submitting}
            className="bg-primary text-primary-foreground w-full rounded-lg px-4 py-3 text-sm font-semibold disabled:opacity-60"
          >
            {checking ? 'Checking access…' : submitting ? 'Verifying…' : 'Continue'}
          </button>
          {error && (
            <p role="alert" className="text-destructive text-sm">
              {error}
            </p>
          )}
        </form>

        <div className="text-muted-foreground mt-6 border-t pt-5 text-xs leading-5">
          <p className="text-foreground font-semibold">Privacy</p>
          <p className="mt-1">
            LiveKit processes microphone audio to carry the call. This demo disables LiveKit Agent
            session recording, so it does not retain this call&apos;s audio, transcript, traces, or
            session logs in Agent Insights. The app does not save your DAF, transcript, or scores.
            The interview transcript is sent to the configured evaluator model for feedback; that
            provider&apos;s data policy applies. The default free NVIDIA model says requests may be
            logged and used to improve NVIDIA products. Please do not share sensitive personal
            information.
          </p>
          <a
            className="mt-2 inline-block underline underline-offset-2"
            href="https://openrouter.ai/nvidia/nemotron-3.5-lightning:free"
            target="_blank"
            rel="noreferrer"
          >
            Default evaluator model data policy
          </a>
          <br />
          <a
            className="mt-2 inline-block underline underline-offset-2"
            href="https://docs.livekit.io/testing/observability/insights/"
            target="_blank"
            rel="noreferrer"
          >
            LiveKit session data and retention details
          </a>
        </div>
      </section>
    </div>
  );
}
