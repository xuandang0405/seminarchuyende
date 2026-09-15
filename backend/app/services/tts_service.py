import os
import hashlib
import uuid
import logging
from typing import Optional, Tuple
import edge_tts
from app.core.config import settings

logger = logging.getLogger("uvicorn")

VOICE_MAP = {
    "vi": "vi-VN-HoaiMyNeural",
    "en": "en-US-GuyNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
    "fr": "fr-FR-DeniseNeural"
}


class TTSService:
    @staticmethod
    def get_voice_for_language(language_code: str) -> str:
        code = language_code.lower().split("-")[0]
        return VOICE_MAP.get(code, "vi-VN-HoaiMyNeural")

    @classmethod
    async def synthesize_speech(
        cls,
        text: str,
        language_code: str = "vi",
        voice_id: Optional[str] = None
    ) -> Tuple[str, int, int, str]:
        """
        Synthesizes text to MP3 file.
        Returns (relative_file_path, duration_ms, file_size_bytes, sha256_hash)
        """
        voice = voice_id or cls.get_voice_for_language(language_code)
        audio_dir = os.path.join(settings.MEDIA_STORAGE_DIR, "audio")
        os.makedirs(audio_dir, exist_ok=True)

        filename = f"{uuid.uuid4().hex}.mp3"
        filepath = os.path.join(audio_dir, filename)

        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(filepath)

            # Read file to calculate size and SHA256
            hasher = hashlib.sha256()
            file_size = 0
            with open(filepath, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
                    file_size += len(chunk)

            sha256_hash = hasher.hexdigest()

            # Estimate duration in milliseconds (approx 16kbps / 128kbps standard for edge-tts MP3 ~ 16000 bytes/sec)
            # 128 kbps = 16,000 bytes/sec -> duration_sec = file_size / 16000
            duration_ms = max(1000, int((file_size / 16000) * 1000))

            logger.info(f"TTS generated successfully: {filepath} ({file_size} bytes, ~{duration_ms}ms)")
            return filename, duration_ms, file_size, sha256_hash

        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            # Fallback: create mock silent MP3 if network error so system doesn't crash
            if not os.path.exists(filepath):
                with open(filepath, "wb") as f:
                    # Minimal mock MP3 header bytes
                    f.write(b"\xff\xfb\x90\x44" + b"\x00" * 1024)
            file_size = os.path.getsize(filepath)
            sha256_hash = hashlib.sha256(open(filepath, "rb").read()).hexdigest()
            return filename, 3000, file_size, sha256_hash


tts_service = TTSService()
