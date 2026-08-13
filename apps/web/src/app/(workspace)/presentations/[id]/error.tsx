"use client";

import { Button } from "@/components/ui/button";

export default function PresentationError({ reset }: { reset: () => void }) {
  return (
    <div className="mx-auto max-w-xl px-4 py-20 text-center">
      <h1 className="text-2xl font-semibold">Could not open this presentation</h1>
      <p className="mt-3 text-[var(--text-muted)]">
        The presentation does not exist, or you do not have access to it.
      </p>
      <Button className="mt-6" onClick={reset}>Try again</Button>
    </div>
  );
}
