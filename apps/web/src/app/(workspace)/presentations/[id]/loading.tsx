export default function PresentationLoading() {
  return (
    <div className="grid min-h-[calc(100dvh-4rem)] animate-pulse place-items-center p-6">
      <div className="aspect-video w-full max-w-4xl rounded-xl bg-[var(--surface-muted)]" />
    </div>
  );
}
