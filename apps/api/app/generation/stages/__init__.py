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
from .content_understanding import (
    StubContentUnderstanding,
    build_content_understanding,
)
from .content_writer import OutlineContentWriter, ProviderContentWriter
from .deck_planner import OutlineDeckPlanner, ProviderDeckPlanner
from .layout_selector import PresentonLayoutSelector
from .orchestrator import GenerationPipeline, SlideValidationFailed
from .protocols import (
    AssetGenerator,
    AssetPlanner,
    ContentGenerator,
    ContentUnderstanding,
    ContentWriter,
    DeckPlanner,
    LayoutSelector,
    SlidePlanner,
    SlideRepairer,
    SlideValidator,
    StoryPlanner,
)
from .slide_repairer import DeterministicSlideRepairer
from .slide_validator import (
    RuleBasedSlideValidator,
    SlideValidationIssue,
    SlideValidationResult,
)
from .slide_planner import OutlineSlidePlanner, ProviderSlidePlanner

__all__ = [
    "AssetGenerator",
    "AssetPlan",
    "AssetPlanner",
    "AssetRequest",
    "AssetSlot",
    "AssetSlotKind",
    "build_content_generator",
    "build_content_understanding",
    "ContentGenerator",
    "ContentUnderstanding",
    "ContentUnderstandingResult",
    "ContentWriter",
    "DeckPlanner",
    "StubContentUnderstanding",
    "GeneratedAsset",
    "GenerationPipeline",
    "ImageAssetGenerator",
    "NullAssetGenerator",
    "LayoutSelector",
    "NativeContentGenerator",
    "OutlineContentWriter",
    "OutlineDeckPlanner",
    "OutlineSlidePlanner",
    "ProviderDeckPlanner",
    "ProviderContentWriter",
    "ProviderSlidePlanner",
    "PresentonLayoutSelector",
    "PresentonContentGenerator",
    "StoryOutline",
    "SlideValidationFailed",
    "SlideValidationIssue",
    "SlideValidationResult",
    "SlidePlanner",
    "SlideRepairer",
    "SlideValidator",
    "DeterministicSlideRepairer",
    "RuleBasedSlideValidator",
    "StubAssetPlanner",
    "ThemeDispatchContentGenerator",
    "StoryOutlineItem",
    "StoryPlanner",
    "VisualIntentAssetPlanner",
]
