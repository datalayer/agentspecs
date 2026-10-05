# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The voice catalogue (VOICE.md VO-40, VO-04) and the Appspec's voice (VO-41, VO-42)."""

import pytest
from pydantic import ValidationError

from agentspecs import speech
from agentspecs.apps import AppError, RecordItem, app_problems, dump_app, list_apps, parse_app


def _app(**changes):
    data = dump_app(next(app for app in list_apps() if app.kind.value == "chat"))
    data.pop("deployment", None)
    data.update(changes)
    return data


def test_every_voice_and_model_loads_and_is_admitted():
    """Nothing in the catalogue has a licence the register refuses: loading it would have raised."""
    book = speech.register()
    for model in speech.list_speech_models():
        speech.check_licences(model.id, model.licence, list(model.where), book)
    for voice in speech.list_voices():
        speech.check_licences(voice.id, voice.licence, list(voice.where), book)
    assert speech.list_voices() and speech.list_speech_models()


@pytest.mark.parametrize(
    "licence",
    [
        "CC-BY-NC-SA-4.0",
        "CC-BY-NC-4.0",
        "Blizzard-2013",
        "Moonshine-Community-License",
        "CPML",
        "proprietary",
    ],
)
def test_a_non_commercial_voice_is_refused(licence):
    """A Piper `ryan`, a `lessac`, a legacy Moonshine, XTTS: refused with a sentence (VO-04)."""
    voice = speech.get_voice("kokoro-af-heart").model_dump()
    voice["licence"] = {"weights": licence}
    with pytest.raises(speech.SpeechCatalogueError, match="is not one the register allows"):
        speech.parse_voice(voice)


def test_a_voice_trained_on_non_commercial_data_is_refused():
    voice = speech.get_voice("kokoro-ff-siwis").model_dump()
    voice["licence"]["dataset"] = "CC-BY-NC-SA-4.0"
    with pytest.raises(speech.SpeechCatalogueError, match="its data"):
        speech.parse_voice(voice)


def test_a_non_commercial_model_is_refused():
    model = speech.get_speech_model("moonshine-tiny-en").model_dump()
    model["licence"]["weights"] = "Moonshine-Community-License"
    with pytest.raises(speech.SpeechCatalogueError):
        speech.parse_speech_model(model)


def test_gpl_runs_on_the_server_and_never_in_the_browser():
    """Decision 1: eSpeak NG's GPL is allowed where it is not distributed."""
    assert speech.admitted("GPL-3.0-or-later", ["server"])
    assert not speech.admitted("GPL-3.0-or-later", ["device"])
    assert not speech.admitted("GPL-3.0-or-later", ["device", "server"])
    model = speech.get_speech_model("whisper-base").model_dump()
    model["licence"]["weights"] = "GPL-3.0-or-later"
    with pytest.raises(speech.SpeechCatalogueError):
        speech.parse_speech_model(model)


def test_every_file_is_pinned_by_its_hash_and_size():
    for model in speech.list_speech_models():
        assert model.files, model.id
        for item in model.files:
            assert len(item.sha256) == 64 and item.size > 0, (model.id, item.path)
    with pytest.raises(ValidationError):
        speech.PinnedFile(path="model.onnx", sha256="not-a-hash", size=1)
    with pytest.raises(ValidationError):
        speech.PinnedFile(path="../elsewhere.onnx", sha256="0" * 64, size=1)


def test_the_first_languages_are_heard_and_spoken():
    """English and French first (decision 12): a voice and a speech-to-text model on the device for each."""
    for language in ("en-US", "fr-FR"):
        assert speech.list_voices(language), language
        heard = speech.transcriber_for(language, "device")
        assert heard is not None and heard.task == "stt", language
    assert speech.transcriber_for("en").id.startswith("moonshine-")
    assert speech.transcriber_for("fr").id == "whisper-base"


def test_the_browser_hears_only_mit_moonshine():
    """VO-04: only the MIT Moonshine models, English, are listed."""
    for model in speech.list_speech_models("stt"):
        if model.id.startswith("moonshine-"):
            assert model.licence.weights == "MIT" and model.languages == ["en"], model.id


def test_the_register_names_everything_the_catalogue_uses():
    book = speech.register()
    for item in [*speech.list_speech_models(), *speech.list_voices()]:
        entry = book.entry(item.id)
        assert entry is not None and entry.status == "used", item.id
        assert entry.licence == item.licence.weights, item.id


def test_the_register_refuses_a_used_entry_it_does_not_allow():
    data = speech.register().model_dump()
    data["entries"].append(
        {
            "name": "x",
            "kind": "voice",
            "licence": "CC-BY-NC-4.0",
            "where": "server",
            "status": "used",
            "source": "-",
        }
    )
    with pytest.raises(ValidationError, match="lists do not allow"):
        speech.Register.model_validate(data)


def test_an_attributed_licence_carries_its_attribution():
    for voice in speech.list_voices():
        if voice.licence.dataset == "CC-BY-4.0" or voice.licence.weights == "CC-BY-4.0":
            assert voice.attribution.strip(), voice.id


def test_a_voice_problem_is_a_sentence():
    assert speech.voice_problems("kokoro-af-heart", "en-US") == []
    assert speech.voice_problems("kokoro-af-heart", "en") == []
    assert "does not speak fr-FR" in speech.voice_problems("kokoro-af-heart", "fr-FR")[0]
    assert "no voice named" in speech.voice_problems("piper-lessac")[0]


def test_the_appspec_voice_is_off_unless_said_and_round_trips():
    app = parse_app(_app())
    assert app.interface.voice.enabled is False
    assert "voice" not in (dump_app(app).get("interface") or {})
    voiced = parse_app(
        _app(
            interface={
                "voice": {
                    "enabled": True,
                    "input": "push_to_talk",
                    "output": "always",
                    "voice": "kokoro-ff-siwis",
                    "language": "fr-FR",
                    "where": "server",
                }
            }
        )
    )
    assert dump_app(voiced)["interface"]["voice"] == {
        "enabled": True,
        "output": "always",
        "voice": "kokoro-ff-siwis",
        "language": "fr-FR",
        "where": "server",
    }
    assert app_problems(voiced) == app_problems(parse_app(_app()))


def test_a_voice_not_in_the_catalogue_or_not_speaking_the_language_is_a_problem():
    unknown = parse_app(
        _app(interface={"voice": {"enabled": True, "output": "always", "voice": "piper-lessac"}})
    )
    assert any("no voice named 'piper-lessac'" in problem for problem in app_problems(unknown))
    mute = parse_app(
        _app(
            interface={
                "voice": {
                    "enabled": True,
                    "output": "always",
                    "voice": "kokoro-af-heart",
                    "language": "fr-FR",
                }
            }
        )
    )
    assert any("does not speak fr-FR" in problem for problem in app_problems(mute))


def test_a_language_is_bcp_47():
    with pytest.raises(AppError, match="language"):
        parse_app(_app(interface={"voice": {"enabled": True, "language": "french"}}))


def test_audio_is_kept_only_when_listening_and_never_in_public():
    listening = {"voice": {"enabled": True}}
    kept = parse_app(_app(interface=listening, record={"include": ["conversations", "audio"]}))
    assert RecordItem.AUDIO in kept.record.include
    with pytest.raises(AppError, match="keeps no audio"):
        parse_app(
            _app(
                interface=listening,
                record={"include": ["conversations", "audio"]},
                deployment={"hosted": {"visibility": "public"}},
            )
        )
    with pytest.raises(AppError, match="only when it listens"):
        parse_app(_app(record={"include": ["conversations", "audio"]}))
