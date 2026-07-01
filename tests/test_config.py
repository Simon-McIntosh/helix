"""Tests for the project config loader.

A Helix run is parameterized by a project's ``helix.yaml``: how to invoke the
native worker, the iteration cap, and the oracle gates. Config is runtime data,
distinct from the durable state records in ``schema/helix.yaml``.
"""

import pytest
import yaml
from pydantic import ValidationError

from helix.config import Config, load_config


def _write_config(project, data):
    (project / "helix.yaml").write_text(yaml.safe_dump(data))


def test_load_config_parses_worker_caps_and_gates(tmp_path):
    _write_config(
        tmp_path,
        {
            "repo": ".",
            "worker": {"command": ["cat"], "timeout_s": 30},
            "caps": {"max_iterations": 7},
            "gates": [
                {
                    "id": "tests",
                    "name": "pytest",
                    "tier": "surrogate",
                    "criterion": "the suite passes",
                    "command": "pytest -q",
                }
            ],
        },
    )

    config = load_config(tmp_path)

    assert isinstance(config, Config)
    assert config.worker.command == ["cat"]
    assert config.worker.timeout_s == 30
    assert config.caps.max_iterations == 7
    assert len(config.gates) == 1
    assert config.gates[0].id == "tests"
    assert config.gates[0].tier == "surrogate"


def test_load_config_applies_defaults(tmp_path):
    _write_config(tmp_path, {"worker": {"command": ["cat"]}})

    config = load_config(tmp_path)

    assert config.repo == "."
    assert config.caps.max_iterations >= 1
    assert config.gates == []


def test_load_config_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path)


def test_config_rejects_unknown_keys(tmp_path):
    _write_config(tmp_path, {"worker": {"command": ["cat"]}, "bogus": 1})
    with pytest.raises(ValidationError):
        load_config(tmp_path)
