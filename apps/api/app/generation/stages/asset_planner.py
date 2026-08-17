from __future__ import annotations

from ..provider import GenerationRequest
from .models import AssetPlan, AssetRequest, AssetSlot, StoryOutline, StoryOutlineItem
from .protocols import AssetPlanner


class StubAssetPlanner:
    """Deterministic asset planner for the initial automatic-image slice.

    Only the `split-image` story layout is assigned a generated hero image for
    its `main_visual_panel` slot. Other layouts keep placeholder shapes, which
    keeps generation fast and avoids surprising the user with images on every
    slide.
    """

    name = "stub"

    # Presenton layout id -> primary image slot names in that layout.
    _IMAGE_SLOTS: dict[str, tuple[str, ...]] = {
        "split-image": ("left_media_image",),
        "title_description_image": ("left_media_image",),
        "title_list_of_cards_with_image": ("card_photo",),
        "title_list_of_cards_with_alternating_image": (
            "upper_image_tile",
            "lower_image_tile",
        ),
    }

    def plan(self, outline: StoryOutline, request: GenerationRequest) -> AssetPlan:
        del request
        requests: list[AssetRequest] = []
        for slide_index, item in enumerate(outline.items):
            slots = self._IMAGE_SLOTS.get(item.layout or "")
            if not slots:
                continue
            prompt = self._build_prompt(item.title, item.content)
            for slot_name in slots:
                requests.append(
                    AssetRequest(
                        slot=AssetSlot(
                            slide_index=slide_index,
                            name=slot_name,
                            kind="image",
                        ),
                        prompt=prompt,
                    )
                )
        return AssetPlan(requests=requests)

    def _build_prompt(self, title: str, content: str) -> str:
        parts = [part for part in (title.strip(), content.strip()) if part]
        prompt = " ".join(parts)
        # Image providers have their own prompt limits; keep this bounded.
        return prompt[:1_000]


class VisualIntentAssetPlanner(StubAssetPlanner):
    """Asset planner that plans images using explicit visual intent.

    Instead of asking the image provider to interpret raw slide text, the
    planner translates each slide's role and message into a structured visual
    intent: concept, mood, composition, and a list of clichés to avoid.
    """

    name = "visual-intent"

    _ROLE_MOODS: dict[str, str] = {
        "cover": "bold editorial, premium, confident",
        "hook": "intriguing, atmospheric, human-scale",
        "problem": "tension, documentary, relatable struggle",
        "solution": "clarity, uplift, calm professionalism",
        "big-stat": "minimal, data-forward, impactful",
        "comparison": "balanced, clean dualism",
        "features": "friendly, organized, approachable",
        "case-study": "authentic, real-world, trustworthy",
        "quote": "contemplative, spacious, editorial portrait",
        "team": "warm, collaborative, human",
        "cta": "energetic, decisive, forward motion",
        "summary": "calm, refined, conclusive",
        "content": "professional, supportive, understated",
        "process": "structured, flow, progression",
        "timeline": "linear, milestone, progress",
    }

    _ROLE_AVOID: dict[str, list[str]] = {
        "cover": ["generic handshake", "glowing lightbulb", "jigsaw puzzle"],
        "hook": ["robot", "glowing brain", "stock office meeting"],
        "problem": ["red downward arrow", "sad stick figure", "broken chain"],
        "solution": ["rocket ship", "superhero", "trophy"],
        "big-stat": ["busy infographic", "3D pie chart", "clip art"],
        "comparison": ["boxing gloves", "scales of justice", "versus fire"],
        "features": ["checklist icon", "gear", "cogwheel"],
        "case-study": ["fake testimonial photo", "generic skyline", "trend chart"],
        "quote": ["oversized quotation mark graphic", "speech bubble collage"],
        "team": ["silhouettes", "forced high-five", "cold corporate lineup"],
        "cta": ["megaphone", "finger pressing button", "explosion"],
        "summary": ["checkmark forest", "mountain peak metaphor", "finish line"],
        "content": ["generic business people", "abstract network", "glowing nodes"],
        "process": ["conveyor belt", "factory", "robot arm"],
        "timeline": ["road going to horizon", "calendar icons", "clock faces"],
    }

    def plan(self, outline: StoryOutline, request: GenerationRequest) -> AssetPlan:
        del request
        requests: list[AssetRequest] = []
        for slide_index, item in enumerate(outline.items):
            slots = self._image_slots_for(item)
            if not slots:
                continue
            intent = self._build_visual_intent(item)
            for slot_name in slots:
                requests.append(
                    AssetRequest(
                        slot=AssetSlot(
                            slide_index=slide_index,
                            name=slot_name,
                            kind="image",
                        ),
                        prompt=self._render_prompt(intent),
                        visual_intent=intent,
                    )
                )
        return AssetPlan(requests=requests)

    def _image_slots_for(self, item: StoryOutlineItem) -> tuple[str, ...]:
        # Prefer explicit layout_id, then legacy layout.
        layout_id = item.layout_id or item.layout or ""
        return self._IMAGE_SLOTS.get(layout_id, ())

    def _build_visual_intent(self, item: StoryOutlineItem) -> dict[str, object]:
        role = item.role or item.layout or "content"
        title = item.title.strip()
        content = item.content.strip()
        base_text = f"{title}. {content}".strip()
        return {
            "role": role,
            "concept": title,
            "subject": self._extract_subject(base_text),
            "mood": self._ROLE_MOODS.get(role, "professional, clean, editorial"),
            "composition": self._composition_for(role),
            "avoid": self._ROLE_AVOID.get(role, ["generic stock photo", "clip art"]),
        }

    def _extract_subject(self, text: str) -> str:
        # Simple heuristic: keep the first sentence and remove obvious prefixes.
        first = text.split(".")[0].strip()
        for prefix in ("How", "What", "Why", "The", "A", "An"):
            if first.startswith(prefix + " "):
                return first[len(prefix) + 1 :].strip()
        return first

    def _composition_for(self, role: str) -> str:
        return {
            "cover": "centered subject with negative space for text overlay",
            "hook": "single focal subject, soft depth, room for headline",
            "problem": "real-world scene, human expression, side negative space",
            "solution": "open workspace, warm light, balanced left-right",
            "big-stat": "minimal background, single strong shape, lots of whitespace",
            "comparison": "two balanced visual zones, no busy details",
            "features": "even grid-friendly texture, low detail",
            "case-study": "authentic environment, shallow depth",
            "quote": "portrait or architectural negative space",
            "team": "group at natural distance, candid interaction",
            "cta": "forward motion, clear subject, decisive negative space",
            "summary": "calm texture, no dominant subject",
            "content": "subtle texture, supportive background",
            "process": "left-to-right visual flow",
            "timeline": "horizontal progression, milestone spacing",
        }.get(role, "balanced composition with negative space for slide text")

    def _render_prompt(self, intent: dict[str, object]) -> str:
        subject = str(intent.get("subject") or "presentation topic")
        mood = str(intent.get("mood") or "professional")
        composition = str(intent.get("composition") or "")
        avoid_list = intent.get("avoid")
        avoid = ", ".join(avoid_list) if isinstance(avoid_list, list) else "generic stock photo"
        return (
            f"Editorial photograph for a presentation slide about {subject}. "
            f"Mood: {mood}. Composition: {composition}. "
            f"Avoid: {avoid}. Clean, modern, premium, no text, no logos."
        )[:1_000]
