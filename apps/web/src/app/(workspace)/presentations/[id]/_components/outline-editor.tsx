"use client";

import {
  closestCenter,
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { DotsSixVertical } from "@phosphor-icons/react";

import { Input } from "@/components/ui/input";
import type { OutlineSlide } from "@/features/presentations/api";

export function OutlineEditor({
  items,
  onChange,
}: {
  items: OutlineSlide[];
  onChange: (items: OutlineSlide[]) => void;
}) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  function updateItem(id: string, patch: Partial<OutlineSlide>) {
    onChange(items.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = items.findIndex((item) => item.id === active.id);
    const newIndex = items.findIndex((item) => item.id === over.id);
    onChange(arrayMove(items, oldIndex, newIndex));
  }

  return (
    <div className="grid gap-3">
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={items} strategy={verticalListSortingStrategy}>
          {items.map((item, index) => (
            <SortableOutlineItem key={item.id} item={item} index={index} onChange={updateItem} />
          ))}
        </SortableContext>
      </DndContext>
    </div>
  );
}

function SortableOutlineItem({
  item,
  index,
  onChange,
}: {
  item: OutlineSlide;
  index: number;
  onChange: (id: string, patch: Partial<OutlineSlide>) => void;
}) {
  const { attributes, listeners, setActivatorNodeRef, setNodeRef, transform, transition, isDragging } = useSortable({ id: item.id });

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={`grid gap-4 rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4 sm:grid-cols-[auto_minmax(0,1fr)] sm:items-start ${isDragging ? "z-10 opacity-70 shadow-lg" : ""}`}
    >
      <button
        ref={setActivatorNodeRef}
        type="button"
        className="flex min-h-10 cursor-grab items-center text-[var(--text-subtle)] active:cursor-grabbing"
        aria-label={`Reorder ${item.title}`}
        {...attributes}
        {...listeners}
      >
        <DotsSixVertical size={22} aria-hidden="true" />
      </button>
      <div className="grid gap-3">
        <label className="grid gap-1.5 text-xs font-medium text-[var(--text-muted)]">
          Slide {index + 1} title
          <Input value={item.title} maxLength={180} onChange={(event) => onChange(item.id, { title: event.target.value })} />
        </label>
        <label className="grid gap-1.5 text-xs font-medium text-[var(--text-muted)]">
          Objective
          <Input value={item.objective} maxLength={500} onChange={(event) => onChange(item.id, { objective: event.target.value })} />
        </label>
        <label className="grid gap-1.5 text-xs font-medium text-[var(--text-muted)]">
          Key points <span className="font-normal text-[var(--text-subtle)]">one per line</span>
          <textarea
            value={item.key_points.join("\n")}
            rows={3}
            className="w-full resize-y rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-sm outline-none focus:border-[var(--accent)]"
            onChange={(event) => onChange(item.id, { key_points: event.target.value.split("\n").slice(0, 6) })}
          />
        </label>
      </div>
    </div>
  );
}
