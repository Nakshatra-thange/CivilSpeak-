'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: (language: string, intensity: string) => void;
}

export function WelcomeView({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) {
  const [language, setLanguage] = useState('English');
  const [intensity, setIntensity] = useState('Standard');
  return (
    <div ref={ref} className="bg-background min-h-screen px-5 py-10 sm:py-16">
      <main className="mx-auto max-w-3xl">
        <p className="text-muted-foreground font-mono text-xs tracking-widest uppercase">
          SuperKalam · Voice Mock
        </p>
        <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">
          UPSC Personality Test
        </h1>
        <p className="text-muted-foreground mt-3 text-lg">
          Practice a UPSC Personality Test with an AI board, in English or Hinglish.
        </p>
        <section className="mt-9 grid gap-6 sm:grid-cols-2">
          <article className="bg-card rounded-2xl border p-5">
            <h2 className="font-semibold">How it works</h2>
            <ol className="text-muted-foreground mt-3 list-inside list-decimal space-y-2 text-sm">
              <li>You speak with the board.</li>
              <li>The board follows up on what you say.</li>
              <li>You get scored feedback.</li>
            </ol>
          </article>
          <article className="bg-card rounded-2xl border p-5">
            <h2 className="font-semibold">What to expect</h2>
            <p className="text-muted-foreground mt-3 text-sm">
              About 8–10 questions, up to 15 minutes.
            </p>
            <h3 className="mt-4 text-sm font-medium">A few tips</h3>
            <p className="text-muted-foreground mt-1 text-sm">
              Use headphones and find a quiet place. Speak naturally. Say “give me a moment” if you
              need to think.
            </p>
          </article>
        </section>
        <section className="mt-6 grid gap-5 sm:grid-cols-2">
          <label className="text-sm font-medium">
            Interview language
            <select
              className="bg-background mt-2 block w-full rounded-lg border p-3"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              <option>English</option>
              <option>Hindi</option>
              <option>Hinglish</option>
            </select>
          </label>
          <label className="text-sm font-medium">
            Board intensity
            <select
              className="bg-background mt-2 block w-full rounded-lg border p-3"
              value={intensity}
              onChange={(e) => setIntensity(e.target.value)}
            >
              <option>Gentle — supportive, more thinking time</option>
              <option>Standard — realistic probing</option>
              <option>Tough — pointed, respectful challenge</option>
            </select>
          </label>
        </section>
        <p className="text-muted-foreground mt-5 text-xs leading-5">
          Privacy: LiveKit processes microphone audio. The demo disables session recording; the app
          does not save your DAF, transcript, or scores. The transcript is sent to the configured
          evaluator model.{' '}
          <a className="underline" href="#privacy">
            Read the full privacy details
          </a>
          .
        </p>
        <div id="privacy" className="text-muted-foreground mt-2 text-xs leading-5">
          The evaluator provider’s data policy applies. The default free NVIDIA model says requests
          may be logged and used to improve NVIDIA products. Please do not share sensitive personal
          information.{' '}
          <a
            className="underline"
            href="https://docs.livekit.io/testing/observability/insights/"
            target="_blank"
            rel="noreferrer"
          >
            LiveKit session data and retention details
          </a>
          .
        </div>
        <Button
          size="lg"
          onClick={() => onStartCall(language, intensity.split(' — ')[0].toLowerCase())}
          className="mt-7 w-full sm:w-auto"
        >
          {startButtonText}
        </Button>
      </main>
    </div>
  );
}
