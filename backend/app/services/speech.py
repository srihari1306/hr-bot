import os
import base64
import json
import tempfile
import azure.cognitiveservices.speech as speechsdk
from pydub import AudioSegment


def get_speech_config():
    config = speechsdk.SpeechConfig(
        subscription=os.environ["AZURE_SPEECH_KEY"],
        region=os.environ["AZURE_SPEECH_REGION"]
    )
    config.speech_recognition_language = "en-US"
    config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    )
    return config


def transcribe_audio(audio_base64: str) -> tuple[str, float]:
    """
    Accepts base64-encoded WebM audio.
    Converts to 16 kHz mono WAV (required by Azure Speech SDK), then transcribes.
    Returns (transcript, confidence). Confidence is 0.0–1.0.
    """
    audio_bytes = base64.b64decode(audio_base64)

    # Write the raw WebM to a temp file
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(audio_bytes)
        webm_path = f.name

    # Convert WebM → 16 kHz mono WAV (Azure Speech SDK supported format)
    wav_path = webm_path.replace(".webm", ".wav")
    try:
        audio = AudioSegment.from_file(webm_path, format="webm")
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        audio.export(wav_path, format="wav")
    finally:
        os.unlink(webm_path)

    config = get_speech_config()
    audio_input = speechsdk.AudioConfig(filename=wav_path)
    recognizer = speechsdk.SpeechRecognizer(
        speech_config=config,
        audio_config=audio_input
    )

    result = recognizer.recognize_once()

    os.unlink(wav_path)

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        # Extract confidence from JSON details if available
        try:
            details = json.loads(result.json)
            confidence = details["NBest"][0]["Confidence"]
        except Exception:
            confidence = 1.0
        return result.text, confidence

    elif result.reason == speechsdk.ResultReason.NoMatch:
        return "", 0.0

    else:
        error_details = ""
        if hasattr(result, "cancellation_details") and result.cancellation_details:
            error_details = result.cancellation_details.error_details
        raise RuntimeError(f"STT failed: {result.reason} — {error_details}")


def synthesize_speech(text: str) -> bytes:
    """
    Returns MP3 bytes for the given text.
    """
    config = get_speech_config()
    # Use a natural neural voice
    config.speech_synthesis_voice_name = "en-US-JennyNeural"

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=config,
        audio_config=None   # no speaker output — capture to bytes
    )

    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return result.audio_data
    else:
        raise RuntimeError(f"TTS failed: {result.reason}")
