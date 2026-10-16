# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The voice catalogue (VOICE.md VO-40, VO-04) and the Appspec's voice (VO-41, VO-42)."""

import pytest
from pydantic import ValidationError

from agentspecs import speech
from agentspecs.apps import (
    AppError,
    RecordItem,
    app_problems,
    dump_app,
    json_schema,
    list_apps,
    parse_app,
)


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


def test_each_model_is_kept_under_its_provider_the_organisation_its_upstream_names():
    """Datalayer's storage keeps a model's files at `<provider>/<model id>/<path>` (VO-48)."""
    for model in speech.list_speech_models():
        organisation = model.source.upstream.rstrip("/").split("/")[3].lower()
        assert model.provider == organisation, model.id
        assert model.folder == f"{model.provider}/{model.id}"
    assert speech.get_speech_model("kokoro-82m").folder == "hexgrad/kokoro-82m"
    unsaid = speech.get_speech_model("silero-vad").model_dump()
    del unsaid["provider"]
    with pytest.raises(ValidationError):
        speech.parse_speech_model(unsaid)
    shouted = speech.get_speech_model("silero-vad").model_dump()
    shouted["provider"] = "Snakers4/x"
    with pytest.raises(ValidationError):
        speech.parse_speech_model(shouted)


def test_the_first_languages_are_heard_and_spoken():
    """English and French first (decision 12): a voice and a speech-to-text model on the device for each."""
    for language in ("en-US", "fr-FR"):
        assert speech.list_voices(language), language
        heard = speech.transcriber_for(language, "device")
        assert heard is not None and heard.task == "stt", language
    assert speech.transcriber_for("en").id == "moonshine-tiny-en"
    assert speech.transcriber_for("fr").id == "whisper-base"


def test_the_server_hears_the_first_languages_with_whisper_turbo():
    """VO-34, decision 4: faster-whisper large-v3-turbo on the server, never sent to a browser."""
    for language in ("en-US", "fr-FR"):
        heard = speech.transcriber_for(language, "server")
        assert heard is not None and heard.id == "whisper-large-v3-turbo", language
    turbo = speech.get_speech_model("whisper-large-v3-turbo")
    assert turbo.where == ["server"] and turbo.engine == "faster-whisper"
    assert turbo.folder == "openai/whisper-large-v3-turbo"
    assert {item.path for item in turbo.files} >= {"model.bin", "config.json", "tokenizer.json"}



def test_the_server_hears_short_turns_with_whisper_small():
    """VO-47 (decided 2026-10-15): a smaller Whisper for turns, never sent to a browser."""
    small = speech.get_speech_model("whisper-small")
    assert small.where == ["server"] and small.engine == "faster-whisper"
    assert small.folder == "openai/whisper-small"
    assert small.size < speech.get_speech_model("whisper-large-v3-turbo").size / 3
    # Long recordings, and the language's server model, stay turbo's.
    assert speech.transcriber_for("fr-FR", "server").id == "whisper-large-v3-turbo"


def test_moonshine_base_is_on_the_server_beside_whisper_small():
    """Decision 18 (2026-10-16): Moonshine base, the browser's own pinned files, run on the server by onnxruntime."""
    server = speech.get_speech_model("moonshine-base-en-server")
    device = speech.get_speech_model("moonshine-base-en")
    assert server.where == ["server"] and server.engine == "onnxruntime"
    assert server.languages == ["en"] and server.licence.weights == "MIT"
    assert server.files == device.files and server.source == device.source
    assert server.folder == "usefulsensors/moonshine-base-en-server"
    assert {item.path for item in server.files} >= {
        "tokenizer.json",
        "config.json",
        "onnx/encoder_model_quantized.onnx",
        "onnx/decoder_model_merged_quantized.onnx",
    }
    # The device's choice is unchanged; the server's model for a language is turbo.
    assert speech.transcriber_for("en", "device").id == "moonshine-tiny-en"
    assert speech.transcriber_for("en", "server").id == "whisper-large-v3-turbo"


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


def test_hands_free_is_a_way_to_talk():
    """VO-12, built 15 October 2026: a conversation by voice, taken as said."""
    app = parse_app(_app(interface={"voice": {"enabled": True, "input": "hands_free"}}))
    assert app.interface.voice.input == "hands_free"
    assert json_schema()["$defs"]["VoiceInput"]["enum"] == ["off", "push_to_talk", "hands_free"]


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


def test_the_voice_extra_is_registered_on_the_person_s_machine():
    """VO-16, VO-01: agent-runtimes' `voice` extra installs these on the person's own machine."""
    book = speech.register()
    on_the_machine = {e.name: e for e in book.entries if e.where == "machine"}
    for name in ("sounddevice", "PortAudio", "kokoro-onnx", "onnxruntime", "espeakng-loader"):
        assert on_the_machine[name].status == "used" and on_the_machine[name].licence == "MIT", name
    # eSpeak NG's GPL is admitted on the server only: on the machine, its notes say it waits on a decision.
    for name in ("phonemizer", "eSpeak NG"):
        entry = book.entry(name)
        assert entry.where == "server" and "person's own machine" in entry.note, name


def test_the_register_refuses_gpl_used_on_the_person_s_machine():
    """Decision 1: GPL is admitted where it is not distributed — the server — and nowhere else."""
    data = speech.register().model_dump()
    data["entries"].append(
        {
            "name": "x",
            "kind": "library",
            "licence": "GPL-3.0-or-later",
            "where": "machine",
            "status": "used",
            "source": "-",
        }
    )
    with pytest.raises(ValidationError, match="lists do not allow"):
        speech.Register.model_validate(data)
