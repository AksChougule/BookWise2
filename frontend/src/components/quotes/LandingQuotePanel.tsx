import { useEffect, useMemo, useState } from "react";

import quotesYaml from "../../content/landing_quotes.yml?raw";

type QuoteEntry = {
  text: string;
  attribution?: string;
};

const ROTATE_MS = 15000;
const FADE_MS = 260;

function parseQuotesYaml(input: string): QuoteEntry[] {
  const lines = input.split(/\r?\n/);
  const quotes: QuoteEntry[] = [];
  let current: Partial<QuoteEntry> | null = null;

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#") || line === "quotes:") {
      continue;
    }

    if (line.startsWith("- text:")) {
      if (current?.text) {
        quotes.push({ text: current.text, attribution: current.attribution });
      }
      const text = line.slice("- text:".length).trim().replace(/^"|"$/g, "");
      current = { text };
      continue;
    }

    if (line.startsWith("attribution:") && current) {
      current.attribution = line.slice("attribution:".length).trim().replace(/^"|"$/g, "");
    }
  }

  if (current?.text) {
    quotes.push({ text: current.text, attribution: current.attribution });
  }

  return quotes;
}

export function LandingQuotePanel() {
  const quotes = useMemo(() => {
    const parsed = parseQuotesYaml(quotesYaml);
    return parsed.length ? parsed : [{ text: "Reading helps ideas stay with you longer." }];
  }, []);

  const [activeIndex, setActiveIndex] = useState(0);
  const [fading, setFading] = useState(false);

  useEffect(() => {
    if (quotes.length <= 1) {
      return;
    }

    let fadeTimer: number | null = null;
    const interval = window.setInterval(() => {
      setFading(true);
      fadeTimer = window.setTimeout(() => {
        setActiveIndex((prev) => (prev + 1) % quotes.length);
        setFading(false);
      }, FADE_MS);
    }, ROTATE_MS);

    return () => {
      window.clearInterval(interval);
      if (fadeTimer !== null) {
        window.clearTimeout(fadeTimer);
      }
    };
  }, [quotes.length]);

  const active = quotes[activeIndex];

  return (
    <section className="landing-quote-panel" aria-live="polite">
      <p className={`landing-quote-text ${fading ? "is-fading" : ""}`}>{`"${active.text}"`}</p>
    </section>
  );
}
