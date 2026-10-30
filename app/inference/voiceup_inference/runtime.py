"""One model instance and a nonblocking admission slot for the whole request."""

import os
import platform
import sys
from collections.abc import Callable
from contextlib import contextmanager
from threading import Lock, Thread
from time import perf_counter, sleep

from voiceup.audio import Turn, validate_turns

from .audio import decode_audio
from .config import Settings
from .errors import InferenceError
from .evidence import extract_pilot_evidence
from .meeting_memory import verify_memory
from .meeting_models import load_meeting_models
from .meeting_runtime import MeetingModels, analyze_meeting_chunk, model_identity
from .model_bundle import DIMENSIONS, MODEL_ID, MODEL_REVISION, BundleError
from .models import ModelHandles, load_models, require_cuda  # noqa: F401


RESPONSE_GRACE_SECONDS = 0.5


def replace_process(settings: Settings, switch: str) -> None:
    """Start the service again in this process, on the settings' processor.

    Reloading in place left the old processor's memory behind: the next CPU job was
    killed for lack of memory in a VM where a freshly started CPU service runs fine.
    """
    environment = {
        **os.environ,
        "VOICEUP_INFERENCE_DEVICE": settings.device,
        "VOICEUP_INFERENCE_RUNTIME_PROFILE": settings.runtime_profile,
        "VOICEUP_INFERENCE_PROCESSOR_SWITCH": switch,
    }
    os.execve(sys.executable, sys.orig_argv, environment)


class InferenceRuntime:
    def __init__(
        self,
        settings: Settings,
        loader: Callable[[Settings], ModelHandles] = load_models,
        meeting_loader: Callable[[Settings], MeetingModels] = load_meeting_models,
        replace: Callable[[Settings, str], None] = replace_process,
    ):
        self.settings = settings
        self._loader = loader
        self._models: ModelHandles | None = None
        self._failure = InferenceError("model_not_ready", "Model is not ready", 503)
        self._slot = Lock()
        self._meeting_loader = meeting_loader
        self._meeting_models: MeetingModels | None = None
        self._meeting_failure = InferenceError(
            "meeting_model_not_ready", "Meeting models are not ready", 503
        )
        self._replace = replace
        self._switching = False
        self._switch_error = (
            "processor_switch_failed" if settings.processor_switch == "returned" else None
        )
        self._switch_thread: Thread | None = None
        self._gpu_profile: str | None = None
        self._gpu_checked = False

    def _gpu_settings(self) -> Settings | None:
        if not self._gpu_checked:
            import torch

            if torch.cuda.is_available():
                self._gpu_profile = {"12.6": "x86_64-cu126", "12.8": "x86_64-cu128"}.get(
                    torch.version.cuda or ""
                )
            self._gpu_checked = True
        if self._gpu_profile is None:
            return None
        return self.settings.model_copy(
            update={"device": "cuda:0", "runtime_profile": self._gpu_profile}
        )

    def _cpu_settings(self) -> Settings | None:
        if platform.machine().lower() not in {"x86_64", "amd64"}:
            return None
        return self.settings.model_copy(
            update={"device": "cpu", "runtime_profile": "x86_64-meeting-cpu"}
        )

    def processor_state(self) -> dict:
        return {
            "device": self.settings.device,
            "gpu_available": self.settings.device != "cpu" or self._gpu_settings() is not None,
            "cpu_available": self.settings.device == "cpu" or self._cpu_settings() is not None,
            "switching": self._switching,
            "last_error": self._switch_error,
        }

    def begin_processor_switch(self, target: str) -> dict:
        """Claim the slot and start again on the selected processor."""
        if (target == "cpu") == (self.settings.device == "cpu"):
            return self.processor_state()
        selected = self._cpu_settings() if target == "cpu" else self._gpu_settings()
        if selected is None:
            raise InferenceError(
                "processor_unavailable", "The selected processor is not available", 409
            )
        if not self._slot.acquire(blocking=False):
            raise InferenceError("inference_busy", "Another inference request is active", 503)
        self._switching, self._switch_error = True, None
        self._start_switch_thread(self._leave_for, selected)
        return self.processor_state()

    def finish_processor_switch(self) -> None:
        """Load in the background after a replacement so the page can follow the progress."""
        self._slot.acquire()
        self._switching = True
        self._start_switch_thread(self._load_selected)

    def join_processor_switch(self) -> None:
        if self._switch_thread is not None:
            self._switch_thread.join()

    def _start_switch_thread(self, target: Callable[..., None], *args: object) -> None:
        self._switch_thread = Thread(target=target, args=args, name="processor-switch", daemon=True)
        self._switch_thread.start()

    def _leave_for(self, selected: Settings) -> None:
        sleep(RESPONSE_GRACE_SECONDS)
        try:
            self._replace(selected, "selected")
        except OSError:
            self._switch_error = "processor_switch_failed"
            self._switching = False
            self._slot.release()

    def _load_selected(self) -> None:
        self.initialize()
        loaded = self._models is not None and (
            not self.settings.meeting_enabled or self._meeting_models is not None
        )
        if not loaded and self.settings.processor_switch == "selected":
            previous = self._gpu_settings() if self.settings.device == "cpu" else self._cpu_settings()
            if previous is not None:
                self._replace(previous, "returned")
                return
        self._switching = False
        self._slot.release()

    def initialize(self) -> None:
        if self._models is not None:
            return
        try:
            self._models = self._loader(self.settings)
        except InferenceError as exc:
            self._failure = exc
        except BundleError:
            self._failure = InferenceError(
                "model_package_invalid", "Model package is invalid", 503
            )
        except Exception:
            # Third-party exceptions may contain paths or remote request details.
            self._failure = InferenceError(
                "model_load_failed", "Local model could not be loaded", 503
            )
        if self.settings.meeting_enabled and self._models is not None:
            try:
                self._meeting_models = self._meeting_loader(self.settings)
            except InferenceError as exc:
                self._meeting_failure = exc
            except Exception:
                self._meeting_failure = InferenceError(
                    "meeting_model_load_failed",
                    "Local meeting models could not be loaded",
                    503,
                )

    def meeting_readiness(self) -> dict:
        self.readiness()
        if not self.settings.meeting_enabled:
            raise InferenceError(
                "meeting_disabled", "Meeting analysis is disabled", 503
            )
        if self._meeting_models is None:
            failure = self._meeting_failure
            raise InferenceError(failure.code, failure.message, failure.status_code)
        return {
            "ready": True,
            "device": self.settings.device,
            "model_identity": model_identity(),
        }

    def meeting_chunk(
        self,
        payload: bytes,
        language: str | None,
        max_speakers: int | None = None,
        num_speakers: int | None = None,
    ) -> dict:
        self.meeting_readiness()
        audio = decode_audio(
            payload,
            self.settings.model_copy(
                update={
                    "max_duration_seconds": 310.0,
                    "max_upload_bytes": 120 * 1024 * 1024,
                }
            ),
            max_decoded_samples=310 * 192000,
            require_mono_pcm16_wav=True,
        )
        assert self._models is not None and self._meeting_models is not None
        try:
            result = analyze_meeting_chunk(
                audio,
                self._meeting_models,
                self._models,
                language,
                max_speakers=max_speakers,
                num_speakers=num_speakers,
            )
        except Exception:
            raise InferenceError(
                "meeting_inference_failed", "Local meeting analysis failed", 503
            ) from None
        result["device"] = self.settings.device
        return result

    def meeting_memory(self, payload: dict) -> dict:
        self.meeting_readiness()
        assert self._models is not None and self._meeting_models is not None
        try:
            with self._meeting_models.voice_embedding_session() as encoder:
                return verify_memory(payload, encoder, self._models, self.settings)
        except InferenceError:
            raise
        except Exception:
            raise InferenceError(
                "meeting_inference_failed", "Local meeting verification failed", 503
            ) from None

    def readiness(self) -> dict:
        if self._models is None:
            # Each readiness probe gets a fresh exception; retaining and raising
            # one instance repeatedly would also retain its growing traceback.
            raise InferenceError(
                self._failure.code, self._failure.message, self._failure.status_code
            )
        return {
            "ready": True,
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "dimensions": DIMENSIONS,
            "device": self.settings.device,
        }

    @contextmanager
    def claim(self):
        self.readiness()
        if not self._slot.acquire(blocking=False):
            raise InferenceError(
                "inference_busy", "Another inference request is active", 503
            )
        try:
            yield
        finally:
            self._slot.release()

    def extract(self, payload: bytes, purpose: str) -> dict:
        """Called while the transport holds the admission slot, including upload."""
        if purpose not in {"enroll", "identify"}:
            raise InferenceError(
                "validation_error", "Purpose must be enroll or identify"
            )
        self.readiness()
        started = perf_counter()
        audio = decode_audio(payload, self.settings)
        models = self._models
        assert models is not None
        try:
            if models.metrics is not None:
                models.metrics.begin()
            spans = models.vad.speech_spans(audio.samples, audio.sample_rate)
            turns = validate_turns(
                [Turn(start, end, "probe") for start, end in spans], audio.duration
            )
            evidence, preprocessing_version = extract_pilot_evidence(
                audio, turns, models.embedder, purpose
            )
            gpu_metrics = models.metrics.finish() if models.metrics is not None else {}
        except Exception:
            raise InferenceError(
                "inference_failed", "Audio inference failed", 503
            ) from None
        if evidence.reason == "inconsistent_voice_windows":
            raise InferenceError(
                "inconsistent_audio", "Speech windows are acoustically inconsistent"
            )
        minimum_seconds, minimum_windows = (10, 2) if purpose == "enroll" else (3, 1)
        if (
            evidence.embedding is None
            or evidence.used_seconds < minimum_seconds - 1e-6
            or evidence.windows < minimum_windows
        ):
            raise InferenceError(
                "insufficient_speech", "Not enough usable single-speaker speech"
            )
        return {
            "embedding": evidence.embedding.tolist(),
            "speech_seconds": evidence.used_seconds,
            "windows_count": evidence.windows,
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "dimensions": DIMENSIONS,
            "device": self.settings.device,
            "quality": {
                "preprocessing_version": preprocessing_version,
                "input_seconds": audio.duration,
                "vad_speech_seconds": evidence.clean_seconds,
                "min_pair_similarity": evidence.consistency,
                "single_speaker_assumption": True,
                "execution_seconds": perf_counter() - started,
                **gpu_metrics,
            },
        }
