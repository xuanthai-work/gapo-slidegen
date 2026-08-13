export default function DashboardLoading() {
  return (
    <div className="mx-auto w-full max-w-[1400px] animate-pulse px-4 py-10 sm:px-6 lg:px-8">
      <div className="h-10 w-72 rounded-lg bg-[var(--surface-muted)]" />
      <div className="mt-4 h-5 w-full max-w-xl rounded bg-[var(--surface-muted)]" />
      <div className="mt-12 grid gap-4 sm:grid-cols-2 xl:max-w-4xl">
        <div className="h-64 rounded-xl bg-[var(--surface-muted)]" />
        <div className="h-64 rounded-xl bg-[var(--surface-muted)]" />
      </div>
    </div>
  );
}
