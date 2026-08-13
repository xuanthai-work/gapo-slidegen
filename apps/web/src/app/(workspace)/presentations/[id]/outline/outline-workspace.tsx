"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  generateOutline,
  getPresentation,
  saveOutline,
  type Outline,
} from "@/features/presentations/api";

import { OutlineEditor } from "../_components/outline-editor";

export function OutlineWorkspace({ id }: { id: string }) {
  const queryClient = useQueryClient();
  const presentationQuery = useQuery({
    queryKey: ["presentations", id],
    queryFn: () => getPresentation(id),
  });
  const [outline, setOutline] = useState<Outline | null>(null);

  const generateMutation = useMutation({
    mutationFn: () => generateOutline(id),
    onSuccess: (generated) => {
      setOutline(generated);
      void queryClient.invalidateQueries({ queryKey: ["presentations"] });
    },
  });
  const saveMutation = useMutation({
    mutationFn: (value: Outline) => saveOutline(id, value),
    onSuccess: (saved) => {
      setOutline(saved);
      void queryClient.invalidateQueries({ queryKey: ["presentations"] });
    },
  });
  const activeOutline = outline ?? presentationQuery.data?.outline ?? null;

  if (presentationQuery.isPending) {
    return <div className="h-72 animate-pulse rounded-xl bg-[var(--surface-muted)]" aria-label="Loading outline" />;
  }

  if (presentationQuery.isError) {
    return (
      <div className="rounded-xl border border-[var(--line)] p-6">
        <p className="font-medium">Could not load this presentation.</p>
        <Button className="mt-4" variant="secondary" onClick={() => presentationQuery.refetch()}>Try again</Button>
      </div>
    );
  }

  if (!activeOutline) {
    return (
      <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-7 text-center">
        <h2 className="text-xl font-semibold">The outline is not ready yet</h2>
        <p className="mx-auto mt-2 max-w-lg text-sm leading-relaxed text-[var(--text-muted)]">
          Generate it from your prompt. If a provider is temporarily unavailable, the configured fallback chain will be tried automatically.
        </p>
        {generateMutation.error ? <p className="mt-4 text-sm text-[var(--danger)]">{generateMutation.error.message}</p> : null}
        <Button className="mt-6" disabled={generateMutation.isPending} onClick={() => generateMutation.mutate()}>
          {generateMutation.isPending ? "Generating outline…" : "Generate outline"}
        </Button>
      </div>
    );
  }

  return (
    <div className="grid gap-5">
      <label className="grid gap-2 text-sm font-medium">
        Presentation title
        <Input value={activeOutline.title} maxLength={240} onChange={(event) => setOutline({ ...activeOutline, title: event.target.value })} />
      </label>
      <OutlineEditor items={activeOutline.slides} onChange={(slides) => setOutline({ ...activeOutline, slides })} />
      {saveMutation.error ? <p className="text-sm text-[var(--danger)]">{saveMutation.error.message}</p> : null}
      <div className="flex items-center justify-end gap-3 border-t border-[var(--line)] pt-5">
        {saveMutation.isSuccess ? <span className="text-sm text-[var(--text-muted)]">Saved</span> : null}
        <Button disabled={saveMutation.isPending} onClick={() => saveMutation.mutate(activeOutline)}>
          {saveMutation.isPending ? "Saving…" : "Save outline"}
        </Button>
      </div>
    </div>
  );
}
