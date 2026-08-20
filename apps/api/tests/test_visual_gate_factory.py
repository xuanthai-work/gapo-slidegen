from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.generation import factory
from app.generation.provider import ProviderConfigurationError
from app.generation.stages.slide_rasterizer import CliSlideRasterizer
from app.generation.stages.visual_gate import CompanyGatewayOcrVisualGate
from app.generation.stub_provider import StubPresentationProvider


def _settings(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "generation_provider": "stub",
        "visual_gate_enabled": False,
        "visual_gate_model": None,
        "visual_gate_max_repairs": 2,
        "visual_gate_rasterizer_cmd": "node packages/slide-rasterizer/dist/cli.js",
        "visual_gate_save_screenshots": False,
        "storage_root": Path(".data/storage"),
        "company_gateway_url": "http://127.0.0.1:5000",
        "company_gateway_api_key": SecretStr("secret"),
        "company_gateway_model": "cb/hnw-llm",
        "company_gateway_chat_path": "/v1/chat/completions",
        "google_max_input_chars": 120_000,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_factory_leaves_gate_off_by_default(monkeypatch) -> None:
    monkeypatch.setattr(factory, "get_settings", lambda: _settings())
    monkeypatch.setattr(factory, "_build_story_planner", lambda: StubPresentationProvider())
    pipeline = factory.build_story_provider()
    assert pipeline.visual_gate is None
    assert pipeline.slide_rasterizer is None


def test_factory_skips_gate_for_stub_even_when_flag_on(monkeypatch, caplog) -> None:
    monkeypatch.setattr(
        factory,
        "get_settings",
        lambda: _settings(visual_gate_enabled=True, visual_gate_model="ocr-vision"),
    )
    monkeypatch.setattr(factory, "_build_story_planner", lambda: StubPresentationProvider())
    with caplog.at_level("WARNING"):
        pipeline = factory.build_story_provider()
    assert pipeline.visual_gate is None
    assert pipeline.slide_rasterizer is None
    assert any("visual gate" in message.lower() for message in caplog.messages)


def test_build_visual_stages_requires_model_when_gateway_flag_on() -> None:
    settings = _settings(
        generation_provider="company-gateway",
        visual_gate_enabled=True,
        visual_gate_model=None,
    )
    with pytest.raises(ProviderConfigurationError, match="SLIDEGEN_VISUAL_GATE_MODEL"):
        factory._build_visual_stages(settings, "company-gateway")


def test_build_visual_stages_requires_model_when_empty_string() -> None:
    settings = _settings(
        generation_provider="company-gateway",
        visual_gate_enabled=True,
        visual_gate_model="  ",
    )
    with pytest.raises(ProviderConfigurationError, match="SLIDEGEN_VISUAL_GATE_MODEL"):
        factory._build_visual_stages(settings, "company-gateway")


def test_build_visual_stages_injects_placeholders_when_enabled() -> None:
    settings = _settings(
        generation_provider="company-gateway",
        visual_gate_enabled=True,
        visual_gate_model="ocr-vision",
    )
    rasterizer, gate = factory._build_visual_stages(settings, "company-gateway")
    assert isinstance(rasterizer, CliSlideRasterizer)
    assert rasterizer.name == "cli"
    assert isinstance(gate, CompanyGatewayOcrVisualGate)
    assert gate.name == "company-gateway-ocr"


def test_factory_wires_visual_stages_for_gateway(monkeypatch) -> None:
    monkeypatch.setattr(
        factory,
        "get_settings",
        lambda: _settings(
            generation_provider="company-gateway",
            visual_gate_enabled=True,
            visual_gate_model="ocr-vision",
            visual_gate_max_repairs=3,
        ),
    )
    monkeypatch.setattr(factory, "_build_story_planner", lambda: StubPresentationProvider())
    pipeline = factory.build_story_provider()
    assert pipeline.visual_gate is not None
    assert pipeline.visual_gate.name == "company-gateway-ocr"
    assert pipeline.slide_rasterizer is not None
    assert pipeline.slide_rasterizer.name == "cli"
    assert pipeline.visual_gate_max_repairs == 3
