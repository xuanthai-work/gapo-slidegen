"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createPresentation, generateOutline } from "@/features/presentations/api";

export function NewPresentationForm() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: async (payload: Parameters<typeof createPresentation>[0]) => {
      const presentation = await createPresentation(payload);
      try {
        await generateOutline(presentation.id);
      } catch {
        // The draft is durable and the outline page provides an explicit retry.
      }
      return presentation.id;
    },
    onSuccess: async (id) => {
      await queryClient.invalidateQueries({ queryKey: ["presentations"] });
      router.push(`/presentations/${id}/outline`);
    },
    onError: (caught) => {
      setError(caught instanceof Error ? caught.message : "Could not create the presentation.");
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const form = new FormData(event.currentTarget);
    mutation.mutate({
      prompt: String(form.get("prompt") ?? ""),
      language: form.get("language") === "vi" ? "vi" : "en",
      slide_count: Number(form.get("slide_count")),
      theme_key: form.get("theme_key") === "gapo-dark" ? "gapo-dark" : "gapo-light",
    });
  }

  return (
    <form onSubmit={handleSubmit} className="mt-10 grid gap-6 rounded-xl border border-[var(--line)] bg-[var(--surface)] p-5 sm:p-7">
      <label className="grid gap-2 text-sm font-medium">
        Topic and requirements
        <textarea
          name="prompt"
          rows={7}
          minLength={10}
          maxLength={4000}
          placeholder="Example: Create a presentation for business leaders about AI use cases that can be piloted within 90 days."
          className="w-full resize-y rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-3 text-sm leading-relaxed outline-none placeholder:text-[var(--text-subtle)] focus:border-[var(--accent)] focus:ring-2 focus:ring-[color-mix(in_srgb,var(--accent)_18%,transparent)]"
          required
        />
        <span className="text-xs font-normal text-[var(--text-subtle)]">
          Do not enter sensitive or confidential internal data during the POC.
        </span>
      </label>

      <div className="grid gap-5 sm:grid-cols-3">
        <label className="grid gap-2 text-sm font-medium">
          Output language
          <select className="min-h-11 rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 outline-none focus:border-[var(--accent)]" name="language" defaultValue="en">
            <option value="en">English</option>
            <option value="vi">Vietnamese</option>
          </select>
        </label>
        <label className="grid gap-2 text-sm font-medium">
          Slide count
          <Input name="slide_count" type="number" min={5} max={10} defaultValue={7} required />
        </label>
        <label className="grid gap-2 text-sm font-medium">
          Theme
          <select className="min-h-11 rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 outline-none focus:border-[var(--accent)]" name="theme_key" defaultValue="gapo-light">
            <option value="gapo-light">Gapo Light</option>
            <option value="gapo-dark">Gapo Dark</option>
          </select>
        </label>
      </div>

      {error ? <p role="alert" className="text-sm text-[var(--danger)]">{error}</p> : null}

      <div className="flex flex-col-reverse gap-3 border-t border-[var(--line)] pt-6 sm:flex-row sm:justify-end">
        <Button asChild variant="ghost"><Link href="/dashboard">Cancel</Link></Button>
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Creating outline…" : "Create outline"}
        </Button>
      </div>
    </form>
  );
}
