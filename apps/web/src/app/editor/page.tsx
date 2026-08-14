import { EditorSpike } from "../editor-spike";

export default async function EditorPage({
  searchParams,
}: {
  searchParams: Promise<{ presentation?: string }>;
}) {
  const { presentation } = await searchParams;
  return <EditorSpike presentationId={presentation} />;
}
