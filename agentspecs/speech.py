# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The voice catalogue: voices, speech models, and the licence register (VOICE.md VO-40).

Three kinds of YAML, beside the other catalogues:

- ``agentspecs/voices/*.yaml`` — the voices an application may speak with:
  the engine and the model that speak it, the engine's own name for it, the
  languages it speaks (BCP 47), where it may run, the licence of its weights
  and of the data it was trained on, and the attribution to show;
- ``agentspecs/speech-models/*.yaml`` — the models behind them and behind
  speech-to-text and voice activity: each file pinned by its SHA-256 and its
  size, so that a model is never fetched from a third party's hub at run time
  and a changed file is refused (VO-03, VO-48);
- ``agentspecs/speech-licences.yaml`` — the register (VO-01): every library,
  model, voice and dataset weighed, with its licence and its source, and the
  two lists a licence is checked against: ``allowed`` (anywhere, the browser
  included) and ``server_only`` (GPL code that runs on Datalayer's servers
  and is never sent to a browser, decision 1).

A voice or a model whose licence is on neither list does not load: the
catalogue refuses it with a sentence (VO-04). Only the dependencies of the
package itself are imported (``pydantic``, ``yaml``), so that the speech
service reads the catalogue without the rest of agentspecs.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_ROOT = Path(__file__).parent

#: Where the voices are.
VOICES_DIR = _ROOT / "voices"

#: Where the speech models are.
SPEECH_MODELS_DIR = _ROOT / "speech-models"

#: The licence register.
REGISTER_PATH = _ROOT / "speech-licences.yaml"

#: Where a step of speech may run: in the person's browser, or on ai-agents.
Where = Literal["device", "server"]

#: What a speech model does.
Task = Literal["stt", "tts", "vad"]

#: A language as BCP 47 writes it, as far as voices need: `en`, `en-US`, `fr-FR`.
_LANGUAGE = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?$")

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SpeechCatalogueError(ValueError):
    """A voice or a model the catalogue refuses, said in a sentence."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Licence(_Strict):
    """The licences a voice or a model is admitted by: its weights, and its training data when it has its own."""

    weights: str = Field(..., description="The licence of the weights, as SPDX names it")
    code: str = Field(
        default="", description="The licence of the code that runs them, when it is the model's own"
    )
    dataset: str = Field(
        default="", description="The licence of the data it was trained on, when it has its own"
    )


class PinnedFile(_Strict):
    """One file of a model, pinned by its hash and its size."""

    path: str = Field(..., description="Its path under the model's folder")
    sha256: str = Field(..., description="Its SHA-256, in hex")
    size: int = Field(..., gt=0, description="Its size, in bytes")

    @field_validator("sha256")
    @classmethod
    def _is_a_hash(cls, value: str) -> str:
        if not _SHA256.match(value):
            raise ValueError(f"{value!r} is not a SHA-256 written in hex")
        return value

    @field_validator("path")
    @classmethod
    def _stays_inside(cls, value: str) -> str:
        if value.startswith("/") or ".." in value.split("/"):
            raise ValueError(f"{value!r} leaves the model's folder")
        return value


class ModelSource(_Strict):
    """Where a model was taken from, once, before it was copied to Datalayer's storage."""

    upstream: str = Field(..., description="The model as its authors published it")
    repository: str = Field(..., description="The export the files were copied from")
    revision: str = Field(..., description="The revision of that export")


class SpeechModel(_Strict):
    """A model of speech: to text, to speech, or voice activity."""

    id: str
    version: str = "0.0.1"
    name: str
    description: str = ""
    task: Task
    engine: str = Field(
        ..., description="What runs it: `transformers.js`, `kokoro-onnx`, `vad-web`"
    )
    dtype: str = Field(
        default="", description="The precision of its weights, as its engine names it"
    )
    languages: List[str] = Field(
        default_factory=list, description="The languages it speaks or hears; none for VAD"
    )
    where: List[Where] = Field(..., min_length=1, description="Where it may run")
    streaming: bool = False
    licence: Licence
    attribution: str = ""
    source: ModelSource
    files: List[PinnedFile] = Field(..., min_length=1)

    @field_validator("languages")
    @classmethod
    def _are_languages(cls, languages: List[str]) -> List[str]:
        for language in languages:
            if not _LANGUAGE.match(language):
                raise ValueError(f"{language!r} is not a language as BCP 47 writes it")
        return languages

    @property
    def size(self) -> int:
        """What a first use downloads, in bytes."""
        return sum(item.size for item in self.files)


class Voice(_Strict):
    """A voice an application may speak with."""

    id: str
    version: str = "0.0.1"
    name: str
    description: str = ""
    engine: str = Field(..., description="The engine that speaks it: `kokoro`")
    model: str = Field(..., description="The speech model it is a voice of, by id")
    voice: str = Field(..., description="The engine's own name for it")
    languages: List[str] = Field(..., min_length=1, description="The languages it speaks, BCP 47")
    where: List[Where] = Field(..., min_length=1, description="Where it may run")
    licence: Licence
    attribution: str = Field(
        default="", description="What the page listing the voices shows, when its licence asks"
    )
    watermark: bool = Field(
        default=False, description="Whether what it says carries a provenance mark"
    )
    sample: str = Field(default="", description="A sentence to hear it say")

    @field_validator("languages")
    @classmethod
    def _are_languages(cls, languages: List[str]) -> List[str]:
        for language in languages:
            if not _LANGUAGE.match(language):
                raise ValueError(f"{language!r} is not a language as BCP 47 writes it")
        return languages

    def speaks(self, language: str) -> bool:
        """Whether it speaks a language: `fr` and `fr-FR` are spoken by a `fr-FR` voice."""
        wanted = language.strip()
        return any(own == wanted or own.split("-")[0] == wanted for own in self.languages)


class RegisterEntry(_Strict):
    """One line of the register."""

    name: str
    kind: Literal["library", "model", "voice", "dataset"]
    version: str = ""
    licence: str
    where: Literal["browser", "server", "tests"]
    status: Literal["used", "candidate", "refused"]
    source: str
    note: str = ""


class Register(_Strict):
    """The licence register (VO-01)."""

    reviewed_by_counsel: bool = False
    checked_on: str
    allowed: List[str] = Field(..., min_length=1)
    server_only: List[str] = Field(default_factory=list)
    entries: List[RegisterEntry]

    @model_validator(mode="after")
    def _used_is_admitted(self) -> Register:
        for entry in self.entries:
            if entry.status != "used":
                continue
            if entry.licence in self.allowed:
                continue
            if entry.licence in self.server_only and entry.where == "server":
                continue
            raise ValueError(
                f"the register uses {entry.name} ({entry.licence}) in the {entry.where}, "
                "which its lists do not allow"
            )
        return self

    def entry(self, name: str) -> Optional[RegisterEntry]:
        for entry in self.entries:
            if entry.name == name:
                return entry
        return None


def _read(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        raise SpeechCatalogueError(f"{path.name} is not a mapping")
    return data


@lru_cache(maxsize=1)
def register() -> Register:
    """The licence register, as it is in the package."""
    return Register.model_validate(_read(REGISTER_PATH))


def admitted(licence: str, where: List[str], book: Optional[Register] = None) -> bool:
    """Whether a licence lets something run where it says: anywhere when allowed, on the server only when GPL."""
    book = book or register()
    if licence in book.allowed:
        return True
    return licence in book.server_only and set(where) == {"server"}


def check_licences(
    name: str, licence: Licence, where: List[str], book: Optional[Register] = None
) -> None:
    """Refuse, in a sentence, a voice or a model whose licences the register does not admit (VO-04)."""
    book = book or register()
    for part, value in (("weights", licence.weights), ("data", licence.dataset)):
        if not value:
            continue
        if not admitted(value, where, book):
            raise SpeechCatalogueError(
                f"{name} is refused: the licence of its {part} ({value}) is not one the register allows "
                f"({', '.join(book.allowed)})"
            )
    if licence.code and not admitted(licence.code, where, book):
        raise SpeechCatalogueError(
            f"{name} is refused: the licence of its code ({licence.code}) is not allowed"
        )


def parse_speech_model(data: Dict[str, Any], book: Optional[Register] = None) -> SpeechModel:
    model = SpeechModel.model_validate(data)
    check_licences(f"The speech model {model.id}", model.licence, list(model.where), book)
    return model


def parse_voice(data: Dict[str, Any], book: Optional[Register] = None) -> Voice:
    voice = Voice.model_validate(data)
    check_licences(f"The voice {voice.id}", voice.licence, list(voice.where), book)
    return voice


@lru_cache(maxsize=1)
def _models() -> Dict[str, SpeechModel]:
    found = {}
    for path in sorted(SPEECH_MODELS_DIR.glob("*.yaml")):
        model = parse_speech_model(_read(path))
        found[model.id] = model
    return found


@lru_cache(maxsize=1)
def _voices() -> Dict[str, Voice]:
    models = _models()
    found = {}
    for path in sorted(VOICES_DIR.glob("*.yaml")):
        voice = parse_voice(_read(path))
        model = models.get(voice.model)
        if model is None or model.task != "tts":
            raise SpeechCatalogueError(
                f"The voice {voice.id} names {voice.model!r}, which is not a text-to-speech model"
            )
        if not set(voice.where) <= set(model.where):
            raise SpeechCatalogueError(
                f"The voice {voice.id} runs where its model {model.id} does not"
            )
        found[voice.id] = voice
    return found


def list_speech_models(task: Optional[str] = None) -> List[SpeechModel]:
    """The speech models, all or those of one task."""
    return [model for model in _models().values() if task is None or model.task == task]


def get_speech_model(model_id: str) -> Optional[SpeechModel]:
    return _models().get(model_id)


def list_voices(language: Optional[str] = None) -> List[Voice]:
    """The voices, all or those that speak a language."""
    return [voice for voice in _voices().values() if language is None or voice.speaks(language)]


def get_voice(voice_id: str) -> Optional[Voice]:
    return _voices().get(voice_id)


def voice_problems(voice_id: str, language: str = "") -> List[str]:
    """What is wrong with a voice an application names, in sentences; empty when nothing is (VO-41)."""
    voice = get_voice(voice_id)
    if voice is None:
        return [f"There is no voice named {voice_id!r} in the voice catalogue."]
    if language and not voice.speaks(language):
        return [
            f"The voice {voice_id!r} does not speak {language}: it speaks {', '.join(voice.languages)}."
        ]
    return []


def transcriber_for(language: str, where: str = "device") -> Optional[SpeechModel]:
    """The speech-to-text model for a language, where it runs: Moonshine where it hears it, Whisper otherwise (decision 3)."""
    base = language.split("-")[0]
    hearing = [
        model
        for model in list_speech_models("stt")
        if where in model.where and base in model.languages
    ]
    for preferred in ("moonshine-base-en", "moonshine-tiny-en"):
        for model in hearing:
            if model.id == preferred:
                return model
    return hearing[0] if hearing else None


__all__ = [
    "REGISTER_PATH",
    "SPEECH_MODELS_DIR",
    "VOICES_DIR",
    "Licence",
    "PinnedFile",
    "Register",
    "RegisterEntry",
    "SpeechCatalogueError",
    "SpeechModel",
    "Voice",
    "admitted",
    "check_licences",
    "get_speech_model",
    "get_voice",
    "list_speech_models",
    "list_voices",
    "parse_speech_model",
    "parse_voice",
    "register",
    "transcriber_for",
    "voice_problems",
]
