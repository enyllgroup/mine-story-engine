"""Keep rejected Blender rendering opt-in and native forwarding shell-free."""
from pathlib import Path
import subprocess
import sys

import pytest

from minestory import __main__ as cli


@pytest.mark.parametrize("arguments", [
    ["produce", "voice.wav"],
    ["produce", "voice.wav", "--director", "session"],
    ["prepare", "voice.wav"],
    ["finish", "old-job"],
    ["render", "storyboard.json", "--audio", "voice.wav", "--output", "job"],
    ["launcher"],
])
def test_old_visual_entrypoints_do_not_invoke_pipeline_by_default(monkeypatch, capsys, arguments):
    from minestory import launcher, pipeline, session
    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("Legacy production must not run without explicit opt-in")

    monkeypatch.setattr(pipeline, "produce", forbidden)
    monkeypatch.setattr(pipeline, "render_storyboard", forbidden)
    monkeypatch.setattr(session, "prepare", forbidden)
    monkeypatch.setattr(session, "finish", forbidden)
    monkeypatch.setattr(launcher, "launch", forbidden)
    assert cli.main(arguments) == 2
    assert calls == []
    error = capsys.readouterr().err
    assert "Mine-imator" in error and "--legacy-blender" in error
    assert "analyze AUDIO" in error


@pytest.mark.parametrize("arguments", [
    ["produce", "voice.wav", "--legacy-blender"],
    ["--legacy-blender", "produce", "voice.wav"],
])
def test_explicit_legacy_diagnostic_remains_available(monkeypatch, arguments):
    from minestory import pipeline
    calls = []

    def diagnostic(audio, **kwargs):
        calls.append((audio, kwargs))
        return {"status": "diagnostic", "video": "old.mp4", "job": "old-job"}

    monkeypatch.setattr(pipeline, "produce", diagnostic)
    assert cli.main(arguments) == 0
    assert calls[0][0] == Path("voice.wav")
    assert calls[0][1]["quality"] == "final"


@pytest.mark.parametrize("action,script", [
    ("project", "create_mineimator_test_project.py"),
    ("gui", "mineimator_gui.py"),
    ("export", "export_mineimator.py"),
    ("finish", "finish_mineimator.py"),
])
def test_native_stages_forward_exact_arguments_as_a_list(monkeypatch, tmp_path, capsys, action, script):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / script).write_text("# native stage fixture\n")
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 7)

    monkeypatch.setattr(cli.subprocess, "run", run)
    untrusted_path = "input directory/voice; $(touch should-not-exist).wav"
    assert cli.main(["native", action, "--input", untrusted_path, "--quality", "preview"]) == 7
    assert calls == [([sys.executable, str(scripts / script), "--input", untrusted_path,
                      "--quality", "preview"], {"cwd": tmp_path})]
    assert "sem API paga" in capsys.readouterr().err
    assert not (tmp_path / "should-not-exist").exists()


def test_missing_native_stage_never_substitutes_a_renderer(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "ROOT", tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("No subprocess may run for an unavailable stage")

    monkeypatch.setattr(cli.subprocess, "run", forbidden)
    assert cli.main(["native", "export", "project.miproject"]) == 1
    assert "nenhum renderer substituto" in capsys.readouterr().err


def test_isolated_audio_analysis_remains_available(monkeypatch, tmp_path):
    from minestory import audio
    calls = []

    def analyze(path, cache, **kwargs):
        calls.append(path)
        return {"duration": 1, "words": [{"word": "teste", "start": 0, "end": 1}]}

    monkeypatch.setattr(audio, "analyze", analyze)
    assert cli.main(["analyze", "voice.wav", "--output", str(tmp_path / "transcript.json")]) == 0
    assert calls == [Path("voice.wav")]
    assert (tmp_path / "transcript.json").is_file()
