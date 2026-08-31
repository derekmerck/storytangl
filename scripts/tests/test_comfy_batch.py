"""Offline batch-helper contract: templates, provenance, resumable dispatch and collection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
from jinja2 import UndefinedError

import comfy_batch as batch
from tangl.media.media_creators.comfy_forge.comfy_api import ComfyApi

TEMPLATE = '''{
  "1": {"class_type": "Example", "inputs": {
    "text": {{ prompt | tojson }}, "seed": {{ seed }}
    {% for slot, image in images.items() %}, {{ slot | tojson }}: {{ image | tojson }}{% endfor %}
  }}
}'''


@pytest.fixture
def api() -> Mock:
    worker = Mock(spec=ComfyApi)
    worker.endpoint.return_value = "http://worker:8188"
    worker.queue_prompt.side_effect = ["job-1", "job-2", "job-3"]
    worker.upload_image.side_effect = lambda data, *, filename: "uploaded/" + filename
    worker.extract_output_image_refs.side_effect = ComfyApi.extract_output_image_refs
    return worker


def prepare(
    api: Mock, *, images: dict[str, Path] | None = None, count: int = 1
) -> batch.BatchReceipt:
    return batch.prepare_jobs(TEMPLATE, [
        batch.JobInput(params={"prompt": "ink wash", "seed": n}, images=images or {})
        for n in range(count)
    ], api.endpoint())


# CLI tests target an explicit endpoint so they never depend on whether the
# host happens to have a worker configured.
OFFLINE_ENDPOINT = "http://worker:8188"

class TestTemplateAndIdentity:
    def test_json_escaping_types_and_nonrecursive_prompt(self) -> None:
        text = '"Claire"\n\\ {{ missing }} — café'
        result = batch.render_workflow(TEMPLATE, {"prompt": text, "seed": 123}, {})
        assert result["1"]["inputs"] == {"text": text, "seed": 123}

    def test_missing_variable_fails_offline(self) -> None:
        with pytest.raises(ValueError, match="Undefined"):
            batch.render_workflow(TEMPLATE, {"seed": 1}, {})
        with pytest.raises(UndefinedError):
            batch.render_workflow(TEMPLATE, {"prompt": "ink"}, {})

    @pytest.mark.parametrize("template", ['{"nodes": []}', '{}', '[]', '{"prompt": {}}'])
    def test_rejects_non_api_workflows(self, template: str) -> None:
        with pytest.raises(ValueError, match="API-format"):
            batch.render_workflow(template, {}, {})

    def test_source_rename_is_not_new_identity_but_bytes_and_seed_are(
        self, api: Mock, tmp_path: Path
    ) -> None:
        first, renamed = tmp_path / "old.webp", tmp_path / "humane.webp"
        first.write_bytes(b"source")
        renamed.write_bytes(b"source")
        original = prepare(api, images={"source": first})
        same = prepare(api, images={"source": renamed})
        assert original.jobs[0].request_sha256 == same.jobs[0].request_sha256
        changed_seed = prepare(api, images={"source": first}, count=2)
        assert changed_seed.jobs[0].request_sha256 != changed_seed.jobs[1].request_sha256
        renamed.write_bytes(b"different")
        assert original.jobs[0].request_sha256 != prepare(
            api, images={"source": renamed}
        ).jobs[0].request_sha256

    def test_identical_jobs_collapse(self, api: Mock) -> None:
        job = batch.JobInput(params={"prompt": "ink", "seed": 1})
        assert len(batch.prepare_jobs(TEMPLATE, [job, job], api.endpoint()).jobs) == 1


class TestSubmissionReceipts:
    def test_upload_once_actual_remote_binding_and_resume(self, api: Mock, tmp_path: Path) -> None:
        image = tmp_path / "original.webp"
        image.write_bytes(b"unchanged")
        prepared = prepare(api, images={"source": image}, count=2)
        path = tmp_path / "receipts.json"
        batch.submit_jobs(api, prepared, path)
        api.upload_image.assert_called_once()
        assert api.queue_prompt.call_count == 2
        api.get_history.assert_not_called()
        saved = batch.BatchReceipt.model_validate_json(path.read_text())
        assert saved.jobs[0].sources["source"].sha256 == hashlib.sha256(b"unchanged").hexdigest()
        assert saved.jobs[0].submitted_workflow["1"]["inputs"]["source"].startswith("uploaded/")
        assert saved.jobs[0].workflow["1"]["inputs"]["source"].startswith("sha256-")
        resumed = batch.resume_receipt(path, prepared)
        batch.submit_jobs(api, resumed, path)
        assert api.queue_prompt.call_count == 2

    def test_offline_preparation_can_resume_after_source_rename(
        self, api: Mock, tmp_path: Path
    ) -> None:
        old = tmp_path / "old.webp"
        old.write_bytes(b"same")
        receipt = prepare(api, images={"source": old})
        path = tmp_path / "receipts.json"
        batch.save_receipt(path, receipt)
        new = old.rename(tmp_path / "new.webp")
        resumed = batch.resume_receipt(path, prepare(api, images={"source": new}))
        batch.submit_jobs(api, resumed, path)
        assert resumed.jobs[0].sources["source"].path == new

    def test_changed_source_is_not_uploaded(self, api: Mock, tmp_path: Path) -> None:
        source = tmp_path / "source.webp"
        source.write_bytes(b"before")
        receipt = prepare(api, images={"source": source})
        source.write_bytes(b"after")
        with pytest.raises(ValueError, match="Source changed"):
            batch.submit_jobs(api, receipt, tmp_path / "receipts.json")
        api.upload_image.assert_not_called()
        api.queue_prompt.assert_not_called()

    def test_post_timeout_is_durable_and_never_automatically_retried(
        self, api: Mock, tmp_path: Path
    ) -> None:
        receipt = prepare(api)
        path = tmp_path / "receipts.json"
        api.queue_prompt.side_effect = requests.Timeout("lost acknowledgement")
        with pytest.raises(requests.Timeout):
            batch.submit_jobs(api, receipt, path)
        saved = batch.BatchReceipt.model_validate_json(path.read_text())
        assert saved.jobs[0].status == "submission_unknown"
        assert saved.jobs[0].submitted_workflow is not None
        with pytest.raises(ValueError, match="uncertain"):
            batch.submit_jobs(api, saved, path)
        assert api.queue_prompt.call_count == 1

    def test_server_validation_error_is_rejected_not_pending(
        self, api: Mock, tmp_path: Path
    ) -> None:
        response = requests.Response()
        response.status_code = 400
        response._content = b'{"node_errors": {"1": "missing model"}}'
        api.queue_prompt.side_effect = requests.HTTPError("invalid", response=response)
        receipt = prepare(api)
        path = tmp_path / "receipt.json"
        with pytest.raises(requests.HTTPError):
            batch.submit_jobs(api, receipt, path)
        assert receipt.jobs[0].status == "rejected"
        assert "missing model" in receipt.jobs[0].error

    def test_different_batch_or_worker_cannot_reuse_receipt(
        self, api: Mock, tmp_path: Path
    ) -> None:
        receipt = prepare(api)
        path = tmp_path / "receipt.json"
        batch.save_receipt(path, receipt)
        with pytest.raises(ValueError, match="different"):
            batch.resume_receipt(path, prepare(api, count=2))
        receipt.endpoint = "http://other:8188"
        with pytest.raises(ValueError, match="different"):
            batch.resume_receipt(path, receipt)


class TestCollection:
    def test_download_names_cannot_escape_job_directory(self, api: Mock, tmp_path: Path) -> None:
        job = prepare(api).jobs[0]
        job.history = {"outputs": {"save": {"images": [{"filename": "../../elsewhere.webp"}]}}}
        api.fetch_image_bytes.return_value = b"output"
        batch.download_outputs(api, job, tmp_path)
        expected = tmp_path / job.request_sha256 / "000-elsewhere.webp"
        assert Path(job.downloads[0]["path"]) == expected

    def test_download_refuses_different_local_content(self, api: Mock, tmp_path: Path) -> None:
        job = prepare(api).jobs[0]
        job.history = {"outputs": {"save": {"images": [{"filename": "a.webp"}]}}}
        api.fetch_image_bytes.return_value = b"original"
        batch.download_outputs(api, job, tmp_path)
        target = Path(job.downloads[0]["path"])
        target.write_bytes(b"user retouched")
        with pytest.raises(ValueError, match="overwrite"):
            batch.download_outputs(api, job, tmp_path)
        assert target.read_bytes() == b"user retouched"

    def test_download_rejects_repository_destination(self, api: Mock) -> None:
        with pytest.raises(ValueError, match="outside the repository"):
            batch.download_outputs(api, prepare(api).jobs[0], batch.REPO_ROOT / "tmp")
        api.fetch_image_bytes.assert_not_called()

    def test_polls_whole_batch_and_preserves_history_and_all_outputs(
        self, api: Mock, tmp_path: Path
    ) -> None:
        receipt = prepare(api, count=2)
        path = tmp_path / "receipts.json"
        batch.submit_jobs(api, receipt, path)
        success = {"status": {"completed": True, "status_str": "success"}, "outputs": {
            "save": {"images": [
                {"filename": "a.webp", "subfolder": "", "type": "output"},
                {"filename": "b.webp", "subfolder": "nested", "type": "temp"},
            ]},
            "text": {"text": ["extra output"]},
        }}
        api.get_history.side_effect = [None, success, success]
        api.fetch_image_bytes.return_value = b"original media including metadata"
        with patch.object(batch.time, "sleep"):
            assert batch.collect_jobs(api, receipt, path, wait=True, output_dir=tmp_path / "out")
        assert [c.args[0] for c in api.get_history.call_args_list] == ["job-1", "job-2", "job-1"]
        assert api.fetch_image_bytes.call_count == 4
        saved = batch.BatchReceipt.model_validate_json(path.read_text())
        for job in saved.jobs:
            assert job.status == "completed"
            assert job.history == success
            assert len(job.downloads) == 2
            for output in job.downloads:
                assert Path(output["path"]).read_bytes() == b"original media including metadata"
                digest = hashlib.sha256(Path(output["path"]).read_bytes()).hexdigest()
                assert output["sha256"] == digest

    @pytest.mark.parametrize("event", ["execution_error", "execution_interrupted"])
    def test_failed_and_interrupted_jobs_are_terminal(
        self, api: Mock, tmp_path: Path, event: str
    ) -> None:
        receipt = prepare(api)
        path = tmp_path / "receipt.json"
        batch.submit_jobs(api, receipt, path)
        api.get_history.return_value = {"status": {
            "completed": False, "messages": [[event, {"exception_message": "OOM"}]],
        }}
        assert batch.collect_jobs(api, receipt, path)
        assert receipt.jobs[0].status == "failed"
        assert receipt.jobs[0].error == ("OOM" if event == "execution_error" else event)

    def test_partial_outputs_do_not_mean_completion(self, api: Mock, tmp_path: Path) -> None:
        receipt = prepare(api)
        path = tmp_path / "receipt.json"
        batch.submit_jobs(api, receipt, path)
        api.get_history.return_value = {"status": {"completed": False}, "outputs": {
            "preview": {"images": [{"filename": "partial.webp"}]},
        }}
        assert not batch.collect_jobs(api, receipt, path)
        assert receipt.jobs[0].status == "submitted"

    def test_wait_timeout_keeps_prompt_id_for_later_collection(
        self, api: Mock, tmp_path: Path
    ) -> None:
        receipt = prepare(api)
        path = tmp_path / "receipt.json"
        batch.submit_jobs(api, receipt, path)
        api.get_history.return_value = None
        with patch.object(batch.time, "monotonic", side_effect=[0, 2]):
            assert not batch.collect_jobs(api, receipt, path, wait=True, timeout=1)
        assert receipt.jobs[0].prompt_id == "job-1"
        assert receipt.jobs[0].status == "submitted"
        api.cancel_prompt.assert_not_called()
        api.interrupt.assert_not_called()

    def test_completed_non_image_workflow_keeps_outputs(self, api: Mock, tmp_path: Path) -> None:
        receipt = prepare(api)
        path = tmp_path / "receipt.json"
        batch.submit_jobs(api, receipt, path)
        api.get_history.return_value = {"status": {"completed": True}, "outputs": {
            "save": {"audio": [{"filename": "speech.wav"}]},
        }}
        assert batch.collect_jobs(api, receipt, path)
        assert receipt.jobs[0].status == "completed"
        assert "audio" in receipt.jobs[0].history["outputs"]["save"]


class TestCLI:
    def test_collect_can_return_later_and_wait_timeout_exit_is_distinct(
        self, api: Mock, tmp_path: Path
    ) -> None:
        path = tmp_path / "receipts.json"
        receipt = prepare(api)
        batch.submit_jobs(api, receipt, path)
        api.get_history.return_value = None
        with (
            patch.object(batch, "ComfyApi", return_value=api),
            patch.object(batch.time, "monotonic", side_effect=[0, 2]),
        ):
            assert batch.main(["collect", str(path), "--wait", "--timeout", "1"]) == 2
        api.get_history.return_value = {"status": {"completed": True}, "outputs": {}}
        with patch.object(batch, "ComfyApi", return_value=api):
            assert batch.main(["collect", str(path), "--wait"]) == 0
        assert api.queue_prompt.call_count == 1

    @pytest.mark.parametrize("wait", [False, True])
    @pytest.mark.parametrize("mixed", [False, True])
    def test_collect_rejects_unsubmitted_prepared_jobs(
        self, api: Mock, tmp_path: Path, capsys: pytest.CaptureFixture[str],
        wait: bool, mixed: bool,
    ) -> None:
        receipt = prepare(api, count=2 if mixed else 1)
        if mixed:
            receipt.jobs[0].status = "completed"
            receipt.jobs[0].prompt_id = "finished-job"
            receipt.jobs[0].history = {"status": {"completed": True}, "outputs": {}}
        path = tmp_path / "receipts.json"
        batch.save_receipt(path, receipt)
        before = path.read_bytes()
        with patch.object(batch, "ComfyApi", return_value=api):
            assert batch.main([
                "collect", str(path), "--output-dir", str(tmp_path / "out"),
                *(["--wait"] if wait else []),
            ]) == 1
        assert "Submit first" in capsys.readouterr().err
        api.get_history.assert_not_called()
        api.fetch_image_bytes.assert_not_called()
        api.queue_prompt.assert_not_called()
        api.upload_image.assert_not_called()
        assert path.read_bytes() == before

    @pytest.mark.parametrize("status", ["submitting", "submission_unknown"])
    def test_collect_does_not_retry_uncertain_submissions(
        self, api: Mock, tmp_path: Path, capsys: pytest.CaptureFixture[str], status: str,
    ) -> None:
        receipt = prepare(api)
        receipt.jobs[0].status = status
        path = tmp_path / "receipts.json"
        batch.save_receipt(path, receipt)
        before = path.read_bytes()
        with patch.object(batch, "ComfyApi", return_value=api):
            assert batch.main(["collect", str(path), "--wait"]) == 1
        assert "Submit first" not in capsys.readouterr().err
        api.get_history.assert_not_called()
        api.queue_prompt.assert_not_called()
        api.upload_image.assert_not_called()
        assert path.read_bytes() == before

    def test_all_manifest_jobs_validate_before_dispatch(self, api: Mock, tmp_path: Path) -> None:
        template = tmp_path / "workflow.json.j2"
        template.write_text(TEMPLATE)
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps({
            "workflow": template.name,
            "jobs": [
                {"params": {"prompt": "valid", "seed": 1}},
                {"params": {"seed": 2}},
            ],
        }))
        with patch.object(batch, "ComfyApi", return_value=api):
            assert batch.main([
                "batch", str(manifest), "--receipts", str(tmp_path / "receipts.json"),
                "--url", OFFLINE_ENDPOINT,
            ]) == 1
        api.queue_prompt.assert_not_called()
        api.upload_image.assert_not_called()

    def test_dry_run_cartesian_product_is_offline(self, tmp_path: Path) -> None:
        template = tmp_path / "workflow.json.j2"
        template.write_text(TEMPLATE)
        image = tmp_path / "source.webp"
        image.write_bytes(b"source")
        path = tmp_path / "receipts.json"
        with (
            patch.object(ComfyApi, "queue_prompt") as submit,
            patch.object(ComfyApi, "upload_image") as upload,
        ):
            assert batch.main([
                "submit", str(template), "--prompt", "ink", "--prompt", "pixel",
                "--seed", "910", "--seed", "911", "--image", str(image),
                "--receipts", str(path), "--url", OFFLINE_ENDPOINT, "--dry-run",
            ]) == 0
        submit.assert_not_called()
        upload.assert_not_called()
        receipt = batch.BatchReceipt.model_validate_json(path.read_text())
        assert len(receipt.jobs) == 4
        assert all(j.status == "prepared" for j in receipt.jobs)

    def test_manifest_defaults_relative_paths_and_multiple_images(self, tmp_path: Path) -> None:
        (tmp_path / "workflow.json.j2").write_text(TEMPLATE)
        (tmp_path / "one.webp").write_bytes(b"one")
        (tmp_path / "two.webp").write_bytes(b"two")
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps({
            "workflow": "workflow.json.j2", "params": {"prompt": "ink", "seed": 1},
            "jobs": [{"params": {"seed": 2}, "images": {"front": "one.webp", "back": "two.webp"}}],
        }))
        path = tmp_path / "receipts.json"
        assert batch.main([
            "batch", str(manifest), "--receipts", str(path),
            "--url", OFFLINE_ENDPOINT, "--dry-run",
        ]) == 0
        receipt = batch.BatchReceipt.model_validate_json(path.read_text())
        assert receipt.jobs[0].params == {"prompt": "ink", "seed": 2}
        assert set(receipt.jobs[0].sources) == {"front", "back"}

    def test_submit_returns_without_polling(self, api: Mock, tmp_path: Path) -> None:
        template = tmp_path / "workflow.json.j2"
        template.write_text(TEMPLATE)
        with patch.object(batch, "ComfyApi", return_value=api):
            assert batch.main([
                "submit", str(template), "--prompt", "ink", "--seed", "1",
                "--receipts", str(tmp_path / "receipt.json"), "--url", OFFLINE_ENDPOINT,
            ]) == 0
        api.get_history.assert_not_called()

    def test_invalid_wait_options_rejected_before_dispatch(
        self, api: Mock, tmp_path: Path
    ) -> None:
        with patch.object(batch, "ComfyApi", return_value=api):
            assert batch.main([
                "submit", "unused.json", "--timeout", "0",
                "--receipts", str(tmp_path / "receipt.json"), "--url", OFFLINE_ENDPOINT,
            ]) == 1
        api.queue_prompt.assert_not_called()
