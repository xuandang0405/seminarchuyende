"""TTS & audio generation with Google TTS and Edge TTS.

C11 / C12 / C13 / SD07 / AD07 / N02.
Supports Vietnamese, English, French voices.
"""

import os
import asyncio
import hashlib
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import edge_tts
from mutagen import MutagenError

from app.core.config import settings
from app.repositories.audio_repo import audio_repo
from app.repositories.poi_repo import poi_repo
from app.services.audio_metadata import mp3_duration_ms

logger = logging.getLogger("uvicorn")

VOICE_MAPPING = {
    "vi": "vi-VN-HoaiMyNeural",
    "en": "en-US-JennyNeural",
    "fr": "fr-FR-DeniseNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
}


GOOGLE_LANG_MAPPING = {
    "vi": "vi",
    "en": "en",
    "fr": "fr",
    "zh": "zh-CN",
    "ja": "ja",
    "ko": "ko",
}


class TTSService:
    async def synthesize_speech(self, text, language_code="vi", voice_id=None):
        result = await self.generate_audio_for_text(text, language_code)
        if not result["success"]:
            raise RuntimeError(result.get("error", "TTS failed"))
        from pathlib import Path
        from app.services.audio_service import audio_service
        payload = Path(audio_service.get_audio_filepath(result["audio_storage_key"])).read_bytes()
        return result["audio_storage_key"], result["audio_duration_ms"], len(payload), hashlib.sha256(payload).hexdigest()

    @staticmethod
    def get_voice_for_language(lang: str) -> str:
        return VOICE_MAPPING.get(lang.split("-")[0].lower(), "vi-VN-HoaiMyNeural")

    @staticmethod
    def calculate_content_hash(text: str, lang: str, voice: str) -> str:
        """Calculates stable SHA-256 hash of text + lang + voice config."""
        raw = f"{text.strip()}_{lang.lower()}_{voice}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def generate_with_google_tts(
        self, text: str, lang: str = "vi", output_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        result = await self._generate_google_mp3(text, lang, output_filename)
        if result["success"]:
            return result
        return await self._generate_edge_mp3(text, lang, output_filename)

    async def generate_audio_for_text(
        self, text: str, lang: str = "vi", output_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        result = await self._generate_edge_mp3(text, lang, output_filename)
        if result["success"]:
            return result
        return await self._generate_google_mp3(text, lang, output_filename)

    async def _generate_google_mp3(
        self,
        text: str,
        lang: str = "vi",
        output_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generates high-quality standard MP3 narration using Google Text-to-Speech (gTTS)."""
        g_lang = GOOGLE_LANG_MAPPING.get(lang, "vi")
        content_hash = hashlib.sha256(f"google_{text.strip()}_{g_lang}".encode("utf-8")).hexdigest()

        if not output_filename:
            output_filename = f"google_{content_hash[:16]}.mp3"

        audio_dir = os.path.join(settings.MEDIA_STORAGE_DIR, "audio")
        file_path = os.path.join(audio_dir, output_filename)
        storage_key = f"audio/{output_filename}"
        audio_url = f"/storage/{storage_key}"

        try:
            os.makedirs(audio_dir, exist_ok=True)
            from gtts import gTTS

            def _synthesize():
                path = Path(file_path)
                if path.is_file() and path.stat().st_size:
                    try:
                        return path.stat().st_size, mp3_duration_ms(path.read_bytes())
                    except (MutagenError, ValueError):
                        pass

                with NamedTemporaryFile(dir=audio_dir, suffix=".tmp", delete=False) as temp:
                    temp_path = Path(temp.name)
                try:
                    gTTS(text=text, lang=g_lang, timeout=(3, 5)).save(str(temp_path))
                    duration = mp3_duration_ms(temp_path.read_bytes())
                    size = temp_path.stat().st_size
                    temp_path.replace(path)
                    return size, duration
                finally:
                    temp_path.unlink(missing_ok=True)

            file_size, estimated_duration_ms = await asyncio.to_thread(_synthesize)

            return {
                "success": True,
                "audio_url": audio_url,
                "audio_storage_key": storage_key,
                "audio_content_hash": content_hash,
                "audio_duration_ms": estimated_duration_ms,
                "file_size": file_size,
                "provider": "google_tts"
            }
        except Exception as error:
            logger.warning("Google TTS failed for %s (%s)", lang, type(error).__name__)
            return {"success": False, "error": "Dịch vụ Google TTS chưa tạo được audio."}

    async def _generate_edge_mp3(
        self,
        text: str,
        lang: str = "vi",
        output_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generates MP3 audio using Edge-TTS."""
        voice = VOICE_MAPPING.get(lang, "vi-VN-HoaiMyNeural")
        content_hash = self.calculate_content_hash(text, lang, voice)

        if not output_filename:
            output_filename = f"{content_hash[:16]}.mp3"

        audio_dir = os.path.join(settings.MEDIA_STORAGE_DIR, "audio")
        file_path = os.path.join(audio_dir, output_filename)
        storage_key = f"audio/{output_filename}"
        audio_url = f"/storage/{storage_key}"

        try:
            os.makedirs(audio_dir, exist_ok=True)
            if os.path.isfile(file_path) and os.path.getsize(file_path) > 0:
                file_size = os.path.getsize(file_path)
            else:
                import uuid
                temp_path = file_path + "." + uuid.uuid4().hex + ".tmp"
                try:
                    communicate = edge_tts.Communicate(text, voice)
                    await asyncio.wait_for(communicate.save(temp_path), timeout=45)
                    os.replace(temp_path, file_path)
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            # Cache entry is immutable because filename includes the content hash.
            communicate = None

            file_size = os.path.getsize(file_path)
            # Estimate duration in ms (assuming ~128kbps = 16000 bytes/sec)
            from pathlib import Path
            from app.services.audio_metadata import mp3_duration_ms
            estimated_duration_ms = mp3_duration_ms(Path(file_path).read_bytes())

            return {
                "success": True,
                "audio_url": audio_url,
                "audio_storage_key": storage_key,
                "audio_content_hash": content_hash,
                "audio_duration_ms": estimated_duration_ms,
                "file_size": file_size,
                "provider": "edge_tts"
            }
        except Exception as error:
            logger.warning("Edge TTS failed for %s (%s, status=%s)", lang, type(error).__name__, getattr(error, "status", None))
            return {"success": False, "error": "Dịch vụ Edge TTS chưa tạo được audio."}

    async def schedule_poi_tts_task(
        self,
        poi_id: str,
        lang: str,
        requested_by: str,
        provider: str = "google",
        task_id: str = None,
    ) -> Dict[str, Any]:
        """Schedules a durable audio_tasks document and executes generation via Google TTS or Edge-TTS."""
        poi = await poi_repo.get_by_id(poi_id)
        if not poi:
            return {"success": False, "error": "POI không tồn tại."}

        loc = await poi_repo.get_localization_by_lang(poi_id, lang)
        text_to_speak = ""
        if loc and loc.get("description"):
            text_to_speak = f"{loc.get('name', '')}. {loc.get('description', '')}"
        else:
            text_to_speak = f"{poi.get('name', '')}. {poi.get('description', '')}"

        voice = VOICE_MAPPING.get(lang, "vi-VN-HoaiMyNeural")
        input_hash = self.calculate_content_hash(text_to_speak, lang, voice)

        item = {
            "poi_id": poi_id,
            "lang": lang,
            "provider": provider,
            "input_hash": input_hash,
            "status": "queued",
            "input_version": poi.get("content_version", 1),
            "error": None,
        }

        task = await audio_repo.create_task(
            requested_by=requested_by,
            items=[item],
            task_id=task_id,
        )

        return {"success": True, "task_id": task["_id"], "status": task["status"]}


tts_service = TTSService()
