import Link from "next/link";

import { NewPresentationForm } from "./new-presentation-form";

export const metadata = { title: "Create presentation" };

export default function NewPresentationPage() {
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6 lg:py-12">
      <Link href="/dashboard" className="text-sm font-medium text-[var(--text-muted)] hover:text-[var(--text)]">
        Back to dashboard
      </Link>
      <div className="mt-8">
        <h1 className="text-3xl font-semibold tracking-[-0.03em] sm:text-4xl">
          What would you like to present?
        </h1>
        <p className="mt-3 max-w-2xl leading-relaxed text-[var(--text-muted)]">
          Describe the topic and audience. The system will draft an outline for your review.
        </p>
      </div>
      <NewPresentationForm />
    </div>
  );
}
