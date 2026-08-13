import { DashboardContent } from "./dashboard-content";

export const metadata = { title: "Dashboard" };

export default function DashboardPage() {
  return (
    <div className="mx-auto w-full max-w-[1400px] px-4 py-8 sm:px-6 lg:px-8 lg:py-10">
      <div className="max-w-2xl">
        <h1 className="text-3xl font-semibold tracking-[-0.03em] sm:text-4xl">
          Your presentations
        </h1>
        <p className="mt-3 leading-relaxed text-[var(--text-muted)]">
          Create outlines, generate slides, and continue editing from one workspace.
        </p>
      </div>
      <DashboardContent />
    </div>
  );
}
