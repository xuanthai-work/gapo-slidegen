import Link from "next/link";

import { OutlineWorkspace } from "./outline-workspace";

export const metadata = { title: "Review outline" };

export default async function OutlinePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 lg:py-10">
      <Link href="/dashboard" className="text-sm font-medium text-[var(--text-muted)] hover:text-[var(--text)]">
        Back to dashboard
      </Link>
      <div className="mt-7 border-b border-[var(--line)] pb-6">
        <h1 className="text-3xl font-semibold tracking-[-0.03em]">Review outline</h1>
        <p className="mt-2 text-[var(--text-muted)]">
          Edit the content and reorder slides before generating the full deck.
        </p>
      </div>
      <div className="mt-7"><OutlineWorkspace id={id} /></div>
    </div>
  );
}
