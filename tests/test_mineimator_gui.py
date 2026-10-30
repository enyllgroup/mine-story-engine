"""Regression checks for false-positive native project-opening reports."""
from pathlib import Path

from scripts.mineimator_gui import log_checkpoint, new_log_segment, project_load_confirmed


def test_old_success_does_not_confirm_a_new_open_request(tmp_path):
    target = Path("/production/test.miproject")
    log = tmp_path / "native.log"
    log.write_text(f"00:01 Opening project: {target}\n00:01 Project loaded\n")
    checkpoint = log_checkpoint(log)
    with log.open("a") as handle:
        handle.write("00:02 Show popup: unsaved project\n")
    assert not project_load_confirmed(new_log_segment(log, checkpoint), target)


def test_opening_without_completion_or_different_project_is_not_success():
    target = Path("/production/test.miproject")
    assert not project_load_confirmed(f"00:01 Opening project: {target}\n", target)
    assert not project_load_confirmed(
        f"00:01 Opening project: {target}\n"
        "00:02 Opening project: /production/other.miproject\n00:02 Project loaded\n",
        target,
    )


def test_new_native_open_and_later_completion_confirm_load(tmp_path):
    target = Path("/production/test.miproject")
    log = tmp_path / "native.log"
    log.write_text("00:01 Previous unrelated operation\n")
    checkpoint = log_checkpoint(log)
    with log.open("a") as handle:
        handle.write(f"00:02 Opening project: {target}\n00:02 load_format: 34\n00:02 Project loaded\n")
    assert project_load_confirmed(new_log_segment(log, checkpoint), target)
