import { EditorSpike } from "../editor-spike";

export default async function EditorPage({
  searchParams,
}: {
  searchParams: Promise<{ presentation?: string; job?: string }>;
}) {
  const { presentation, job } = await searchParams;
  return <EditorSpike presentationId={presentation} jobId={job} />;
}
