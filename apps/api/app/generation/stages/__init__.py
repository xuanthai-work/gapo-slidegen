"""Generation pipeline stage boundaries.

The orchestrator in this package composes small, single-responsibility stages
into the full generation pipeline used by the worker. Each stage is a protocol
so providers and renderers can be swapped independently.
"""

from .models import (
    AssetPlan,
    AssetRequest,
    AssetSlot,
    AssetSlotKind,
    ContentUnderstandingResult,
    GeneratedAsset,
    StoryOutline,
    StoryOutlineItem,
)
from .asset_generator import ImageAssetGenerator, NullAssetGenerator
from .asset_planner import StubAssetPlanner, VisualIntentAssetPlanner
from .content_generator import (
    NativeContentGenerator,
    PresentonContentGenerator,
    ThemeDispatchContentGenerator,
    build_content_generator,
)
from .orchestrator import GenerationPipeline
from .protocols import (
    AssetGenerator,
    AssetPlanner,
    ContentGenerator,
    ContentUnderstanding,
    LayoutSelector,
    StoryPlanner,
)

__all__ = [
    "AssetGenerator",
    "AssetPlan",
    "AssetPlanner",
    "AssetRequest",
    "AssetSlot",
    "AssetSlotKind",
    "build_content_generator",
    "ContentGenerator",
    "ContentUnderstanding",
    "ContentUnderstandingResult",
    "GeneratedAsset",
    "GenerationPipeline",
    "ImageAssetGenerator",
    "NullAssetGenerator",
    "LayoutSelector",
    "NativeContentGenerator",
    "PresentonContentGenerator",
    "StoryOutline",
    "StubAssetPlanner",
    "ThemeDispatchContentGenerator",
    "StoryOutlineItem",
    "StoryPlanner",
    "VisualIntentAssetPlanner",
]
