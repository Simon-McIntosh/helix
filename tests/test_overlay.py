"""Tests for core-vs-overlay resolution and the anti-drift check.

Overlays extend the packaged phase contracts, never replace them; the check
flags forks mechanically. Synthetic projects live in tmp_path.
"""

import yaml

from helix import overlay


def _project(tmp_path, *, gates=None, plan=None, extra=None):
    config = {"repo": ".", "worker": {"command": ["true"]}, "gates": gates or []}
    if plan:
        config["plan"] = plan
    config.update(extra or {})
    (tmp_path / "helix.yaml").write_text(yaml.safe_dump(config))
    return tmp_path


def test_resolve_returns_the_core_contract_without_an_overlay(tmp_path):
    project = _project(tmp_path)
    resolved = overlay.resolve_prompt(project, "implement")
    assert resolved == overlay._core_prompt("implement").strip() + "\n"
    assert "worker" in resolved  # the packaged implement contract


def test_resolve_appends_the_project_extension(tmp_path):
    project = _project(tmp_path)
    ext = overlay.overlay_path(project, "implement")
    ext.parent.mkdir(parents=True)
    ext.write_text("Domain note: solver logs live in logs/.\n")

    resolved = overlay.resolve_prompt(project, "implement")

    core = overlay._core_prompt("implement").strip()
    assert resolved.startswith(core)
    assert resolved.rstrip().endswith("Domain note: solver logs live in logs/.")


def test_resolve_ignores_a_legacy_replacement_and_check_flags_it(tmp_path):
    project = _project(tmp_path)
    (project / "prompts").mkdir()
    (project / "prompts" / "implement.md").write_text("# my own contract\n")

    resolved = overlay.resolve_prompt(project, "implement")
    assert "my own contract" not in resolved  # never substituted

    problems = overlay.check_project(project)
    assert any("forked core contract" in p for p in problems)


def test_self_hosting_identity_is_not_a_fork():
    # The Helix repo root is itself a project: its prompts/<phase>.md ARE the
    # core contracts (same resolved path), which is sanctioned.
    repo_root = overlay.CORE_PROMPTS_DIR.parent
    problems = [p for p in overlay.check_project(repo_root) if "forked" in p]
    assert problems == []


def test_check_flags_an_overlay_that_restates_the_core(tmp_path):
    project = _project(tmp_path)
    core_heading = overlay._core_prompt("judge").splitlines()[0]
    ext = overlay.overlay_path(project, "judge")
    ext.parent.mkdir(parents=True)
    ext.write_text(core_heading + "\n\nsome domain text\n")

    problems = overlay.check_project(project)
    assert any("restates the core contract" in p for p in problems)


def test_check_flags_an_oversized_overlay(tmp_path):
    project = _project(tmp_path)
    ext = overlay.overlay_path(project, "plan")
    ext.parent.mkdir(parents=True)
    ext.write_text("x" * (len(overlay._core_prompt("plan").encode()) + 1))

    problems = overlay.check_project(project)
    assert any("larger than the core contract" in p for p in problems)


def test_check_flags_gate_problems(tmp_path):
    def gate(gid, name, command=""):
        return {
            "id": gid,
            "name": name,
            "tier": "surrogate",
            "criterion": "c",
            "command": command,
        }

    gates = [gate("g", "a", "true"), gate("g", "b", "true"), gate("h", "c")]
    problems = overlay.check_project(_project(tmp_path, gates=gates))
    assert any("duplicate gate id 'g'" in p for p in problems)
    assert any("surrogate gate 'h' has no command" in p for p in problems)


def test_check_flags_missing_config_and_missing_plan(tmp_path):
    assert any("helix.yaml: missing" in p for p in overlay.check_project(tmp_path))

    project = _project(tmp_path, plan="PLAN.md")
    assert any(
        "configured plan file is missing" in p for p in overlay.check_project(project)
    )


def test_a_clean_project_reports_no_problems(tmp_path):
    project = _project(
        tmp_path,
        gates=[
            {
                "id": "tests",
                "name": "t",
                "tier": "surrogate",
                "criterion": "c",
                "command": "true",
            }
        ],
        plan="PLAN.md",
    )
    (project / "PLAN.md").write_text("## Tasks\n\n- [ ] t\n")
    ext = overlay.overlay_path(project, "implement")
    ext.parent.mkdir(parents=True)
    ext.write_text("One small domain note.\n")

    assert overlay.check_project(project) == []
