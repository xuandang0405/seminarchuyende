"""TTS & Audio Generation Service using Edge-TTS.

C11 / C12 / C13 / SD07 / AD07 / N02.
Supports Vietnamese, English, French voices.
"""

import os
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import edge_tts

from app.core.config import settings
from app.repositories.audio_repo import audio_repo
from app.repositories.poi_repo import poi_repo

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
    @staticmethod
    def get_voice_for_language(lang: str) -> str:
        return VOICE_MAPPING.get(lang.split("-")[0].lower(), "vi-VN-HoaiMyNeural")

    @staticmethod
    def calculate_content_hash(text: str, lang: str, voice: str) -> str:
        """Calculates stable SHA-256 hash of text + lang + voice config."""
        raw = f"{text.strip()}_{lang.lower()}_{voice}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def generate_with_google_tts(
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
        os.makedirs(audio_dir, exist_ok=True)
        file_path = os.path.join(audio_dir, output_filename)
        storage_key = f"audio/{output_filename}"
        audio_url = f"/storage/{storage_key}"

        try:
            from gtts import gTTS
            import asyncio

            def _synthesize():
                tts = gTTS(text=text, lang=g_lang, slow=False)
                tts.save(file_path)

            await asyncio.to_thread(_synthesize)

            file_size = os.path.getsize(file_path)
            estimated_duration_ms = max(int((file_size / 4000.0) * 1000), 3000)

            return {
                "success": True,
                "audio_url": audio_url,
                "audio_storage_key": storage_key,
                "audio_content_hash": content_hash,
                "audio_duration_ms": estimated_duration_ms,
                "file_size": file_size,
                "provider": "google_tts"
            }
        except Exception as e:
            logger.error(f"Google TTS generation error: {e}")
            # Fallback to edge-tts if gTTS encounters network issues
            return await self.generate_audio_for_text(text, lang, output_filename=output_filename)

    async def generate_audio_for_text(
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
        os.makedirs(audio_dir, exist_ok=True)
        file_path = os.path.join(audio_dir, output_filename)
        storage_key = f"audio/{output_filename}"
        audio_url = f"/storage/{storage_key}"

        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(file_path)

            file_size = os.path.getsize(file_path)
            # Estimate duration in ms (assuming ~128kbps = 16000 bytes/sec)
            estimated_duration_ms = max(int((file_size / 16000.0) * 1000), 3000)

            return {
                "success": True,
                "audio_url": audio_url,
                "audio_storage_key": storage_key,
                "audio_content_hash": content_hash,
                "audio_duration_ms": estimated_duration_ms,
                "file_size": file_size,
                "provider": "edge_tts"
            }
        except Exception as e:
            logger.error(f"Edge-TTS generation error: {e}")
            return {"success": False, "error": str(e)}

    async def schedule_poi_tts_task(
        self,
        poi_id: str,
        lang: str,
        requested_by: str,
        provider: str = "google"
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
            "input_hash": input_hash,
            "status": "queued",
            "input_version": poi.get("content_version", 1),
            "error": None,
        }

        task = await audio_repo.create_task(
            requested_by=requested_by,
            items=[item]
        )

        # Execute generation (Google TTS by default as requested by user)
        filename = f"{poi_id}_{lang}.mp3"
        if provider == "google":
            res = await self.generate_with_google_tts(text_to_speak, lang, output_filename=filename)
        else:
            res = await self.generate_audio_for_text(text_to_speak, lang, output_filename=filename)

        if res["success"]:
            await audio_repo.update_audio_metadata(
                poi_id=poi_id,
                lang=lang,
                audio_url=res["audio_url"],
                audio_storage_key=res["audio_storage_key"],
                audio_content_hash=res["audio_content_hash"],
                audio_duration_ms=res["audio_duration_ms"],
                audio_source="tts_generated"
            )
            # Also update the POI directly with the new audio URL
            await poi_repo.update_poi(poi_id, {
                "audio_url": res["audio_url"],
                "audio_duration_ms": res["audio_duration_ms"]
            })
            await audio_repo.finish_task(task["_id"], status="succeeded")
            return {
                "success": True,
                "task_id": task["_id"],
                "audio_url": res["audio_url"],
                "duration_ms": res["audio_duration_ms"],
                "provider": res.get("provider", provider)
            }
        else:
            await audio_repo.finish_task(task["_id"], status="failed", error_message=res.get("error"))
            return {
                "success": False,
                "task_id": task["_id"],
                "error": res.get("error")
            }


tts_service = TTSService()
