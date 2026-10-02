"""Opt-in integration test for Gemini audio-window analysis.

The old version executed FFmpeg and a Gemini request during pytest collection
and depended on an Antigravity-specific absolute path. That made the whole
suite fail before tests could even be collected.

Set STOCKPILE_TEST_AUDIO to a local audio file and
STOCKPILE_RUN_LIVE_GEMINI_TEST=1 to run the real integration test.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


@pytest.mark.integration
def test_gemini_audio_window():
    if os.getenv("STOCKPILE_RUN_LIVE_GEMINI_TEST") != "1":
        pytest.skip("Live Gemini audio test disabled; set STOCKPILE_RUN_LIVE_GEMINI_TEST=1")

    input_value = os.getenv("STOCKPILE_TEST_AUDIO")
    if not input_value:
        pytest.skip("Set STOCKPILE_TEST_AUDIO to a local audio file")

    input_path = Path(input_value).expanduser().resolve()
    if not input_path.is_file():
        pytest.fail(f"STOCKPILE_TEST_AUDIO does not exist: {input_path}")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.fail("GEMINI_API_KEY is missing")

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.fail("ffmpeg is not available on PATH")

    output_path = Path(__file__).with_name("window_0_30.mp3")
    try:
        subprocess.run(
            [ffmpeg, "-y", "-ss", "0", "-t", "30", "-i", str(input_path), str(output_path)],
            check=True,
            capture_output=True,
            text=True,
        )

        client = genai.Client(api_key=api_key)
        audio_file = client.files.upload(file=str(output_path))
        prompt = """
Listen to this 30-second audio clip which contains multiple consecutive meme sound effects and SFX.
List every distinct sound effect in order. Include start_time, end_time, title,
category, and description. Output a JSON array.
"""
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=[audio_file, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )

        result = json.loads(response.text)
        assert isinstance(result, list)
    finally:
        output_path.unlink(missing_ok=True)
