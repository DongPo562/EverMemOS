from pathlib import Path
import os

from core.component.llm.tokenizer.tokenizer_factory import (
    TokenizerFactory,
    get_default_tiktoken_cache_dir,
)


def test_tokenizer_factory_sets_project_cache_dir_by_default(monkeypatch):
    monkeypatch.delenv("TIKTOKEN_CACHE_DIR", raising=False)
    monkeypatch.delenv("DATA_GYM_CACHE_DIR", raising=False)

    TokenizerFactory()

    assert os.environ["TIKTOKEN_CACHE_DIR"] == str(get_default_tiktoken_cache_dir())


def test_tokenizer_factory_preserves_explicit_cache_dir(monkeypatch):
    explicit_cache_dir = Path("D:/custom-tiktoken-cache-for-test")
    monkeypatch.setenv("TIKTOKEN_CACHE_DIR", str(explicit_cache_dir))

    TokenizerFactory()

    assert os.environ["TIKTOKEN_CACHE_DIR"] == str(explicit_cache_dir)
