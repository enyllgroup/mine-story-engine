"""Portable bundles cannot pull files from outside a job or overwrite a file."""
import importlib.util
import json
from pathlib import Path
import zipfile
import pytest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('native_package',ROOT/'scripts/package_native_production.py')
PACKAGE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(PACKAGE)


def test_archive_retains_relative_project_resources_and_passes_crc(tmp_path):
    job=tmp_path/'job';project=job/'mineimator/story.miproject';project.parent.mkdir(parents=True)
    model=project.parent/'assets/object.mimodel';model.parent.mkdir()
    texture=model.parent/'texture.png';texture.write_bytes(b'own texture')
    model.write_text(json.dumps({'texture':'assets/texture.png','parts':[]}))
    project.write_text(json.dumps({'format':34,'resources':[{'type':'model','filename':'assets/object.mimodel'}]}))
    output=tmp_path/'bundle.zip';report=PACKAGE.package(job,project,output)
    assert report['entrypoint']=='mineimator/story.miproject'
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert 'mineimator/assets/texture.png' in archive.namelist()


def test_archive_rejects_an_outside_resource_before_writing(tmp_path):
    job=tmp_path/'job';job.mkdir();outside=tmp_path/'unrelated.txt';outside.write_text('private')
    project=job/'story.miproject';project.write_text(json.dumps({'format':34,'resources':[{'type':'sound','filename':'../unrelated.txt'}]}))
    output=tmp_path/'bundle.zip'
    with pytest.raises(ValueError,match='escapes'):PACKAGE.package(job,project,output)
    assert not output.exists()


def test_archive_preserves_an_existing_download(tmp_path):
    job=tmp_path/'job';job.mkdir();project=job/'story.miproject'
    project.write_text(json.dumps({'format':34,'resources':[]}))
    output=tmp_path/'bundle.zip';output.write_bytes(b'previous download')
    with pytest.raises(FileExistsError):PACKAGE.package(job,project,output)
    assert output.read_bytes()==b'previous download'
