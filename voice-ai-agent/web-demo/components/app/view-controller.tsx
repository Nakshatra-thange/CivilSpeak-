'use client';

import { useEffect, useState } from 'react';
import { useTheme } from 'next-themes';
import { AnimatePresence, motion } from 'motion/react';
import { useAgent, useSessionContext } from '@livekit/components-react';
import { AgentSessionView_01 } from '@/components/agents-ui/blocks/agent-session-view-01';
import { WelcomeView } from '@/components/app/welcome-view';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionSessionView = motion.create(AgentSessionView_01);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: {
      opacity: 1,
    },
    hidden: {
      opacity: 0,
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.5,
    ease: 'linear',
  },
};

interface ViewControllerProps {
  isVideoInputSupported: boolean;
}

export function ViewController({ isVideoInputSupported }: ViewControllerProps) {
  const { isConnected, start, end } = useSessionContext();
  const agent = useAgent();
  const [connecting, setConnecting] = useState(false);
  const [failed, setFailed] = useState(false);
  const [ending, setEnding] = useState(false);
  const [remaining, setRemaining] = useState(15 * 60);
  useEffect(() => {
    if (isConnected) {
      setConnecting(false);
      setFailed(false);
    }
  }, [isConnected]);
  useEffect(() => {
    if (!connecting) return;
    const timeout = window.setTimeout(() => {
      if (!isConnected) {
        setConnecting(false);
        setFailed(true);
      }
    }, 15000);
    return () => window.clearTimeout(timeout);
  }, [connecting, isConnected]);
  useEffect(() => {
    if (!isConnected) return;
    const timer = window.setInterval(() => setRemaining((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearInterval(timer);
  }, [isConnected]);
  const { resolvedTheme } = useTheme();

  return (
    <AnimatePresence mode="wait">
      {/* Welcome view */}
      {!isConnected && !connecting && !failed && (
        <MotionWelcomeView
          key="welcome"
          {...VIEW_MOTION_PROPS}
          startButtonText="Start call"
          onStartCall={() => {
            setFailed(false);
            setConnecting(true);
            void start();
          }}
        />
      )}
      {!isConnected && (connecting || failed) && (
        <section className="bg-background grid min-h-screen place-content-center px-6 text-center">
          <p className="text-muted-foreground">Allow microphone access when your browser asks.</p>
          <h1 className="mt-3 text-2xl font-semibold">
            {failed ? 'Could not connect' : 'Connecting you to the board…'}
          </h1>
          {failed && (
            <>
              <p role="alert" className="mt-2 text-sm">
                The board has not joined yet. Check your connection and try again.
              </p>
              <button
                className="bg-primary text-primary-foreground mt-5 rounded-lg px-5 py-3"
                onClick={() => {
                  setFailed(false);
                  setConnecting(true);
                  void start();
                }}
              >
                Retry
              </button>
            </>
          )}
        </section>
      )}
      {/* Session view */}
      {isConnected && (
        <div className="relative">
          <div className="bg-background/90 fixed top-4 right-4 z-20 flex items-center gap-3 rounded-xl border px-4 py-2 text-sm shadow">
            <span aria-live="polite">
              {agent.state === 'speaking'
                ? 'Speaking'
                : agent.state === 'thinking'
                  ? 'Thinking'
                  : 'Listening'}
            </span>
            <span>
              {Math.floor(remaining / 60)}:{String(remaining % 60).padStart(2, '0')}
            </span>
            <button className="underline" onClick={() => setEnding(true)}>
              End interview
            </button>
          </div>
          <MotionSessionView
            key="session-view"
            {...VIEW_MOTION_PROPS}
            preConnectMessage={
              agent.isConnected ? 'Agent is listening, ask it a question' : 'Waiting for agent'
            }
            supportsChatInput={false}
            supportsVideoInput={isVideoInputSupported}
            supportsScreenShare={isVideoInputSupported}
            isPreConnectBufferEnabled={true}
            themeMode={resolvedTheme === 'dark' ? 'dark' : 'light'}
            className="fixed inset-0"
          />
          {ending && (
            <div
              role="dialog"
              aria-modal="true"
              className="fixed inset-0 z-40 grid place-items-center bg-black/50 p-5"
            >
              <div className="bg-background w-full max-w-sm rounded-xl p-6">
                <h2 className="text-lg font-semibold">End this interview?</h2>
                <p className="text-muted-foreground mt-2 text-sm">
                  You can’t rejoin this session after ending it.
                </p>
                <div className="mt-5 flex justify-end gap-3">
                  <button className="rounded-lg border px-4 py-2" onClick={() => setEnding(false)}>
                    Keep going
                  </button>
                  <button
                    className="bg-destructive rounded-lg px-4 py-2 text-white"
                    onClick={() => {
                      setEnding(false);
                      void end();
                    }}
                  >
                    End interview
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </AnimatePresence>
  );
}
