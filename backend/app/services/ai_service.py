import logging
from typing import Optional
from app.schemas.ai import AINarrationRequest, AINarrationResponse
from app.services.tts_service import tts_service

logger = logging.getLogger("uvicorn")


class AIService:
    @classmethod
    async def generate_narration(cls, req: AINarrationRequest) -> AINarrationResponse:
        """
        Generates context-aware, tourist-friendly narration text.
        Incorporates POI category, specialties, tone, and weather.
        """
        name = req.poi_name
        category = req.category
        weather = req.weather or "mát mẻ dễ chịu"
        specialties_str = ", ".join(req.specialties) if req.specialties else "các món ăn và nét văn hóa đặc trưng"

        # Contextual prompt generator
        weather_phrase = ""
        if "mưa" in weather.lower() or "rain" in weather.lower():
            weather_phrase = "Trong tiết trời se lạnh của cơn mưa Sài Gòn, không gì tuyệt vời hơn khi dừng chân thưởng thức hương vị nóng hổi tại đây."
        elif "nắng" in weather.lower() or "sun" in weather.lower():
            weather_phrase = "Dưới ánh nắng rực rỡ của thành phố, nơi đây mang đến cho bạn không gian sôi động và những trải nghiệm khó quên."
        else:
            weather_phrase = f"Trong không khí {weather} hôm nay, bạn hãy dành chút thời gian lắng nghe câu chuyện đầy thú vị về địa điểm này."

        if req.language_code.startswith("en"):
            title = f"Discovering {name}"
            description = f"An authentic {category} destination in District 4 featuring {specialties_str}."
            narration = (
                f"Welcome to {name}! Located in the heart of Saigon's District 4, "
                f"this spot is renowned for its incredible culinary delights, especially {specialties_str}. "
                f"{weather_phrase} "
                f"Take a moment to savor the aromas, watch the lively local life around you, and enjoy every bite!"
            )
        else:
            title = f"Khám phá {name}"
            description = f"Điểm đến {category} đặc sắc tại Quận 4 với {specialties_str}."
            narration = (
                f"Chào mừng bạn đến với {name}! Tọa lạc giữa lòng Quận 4 - mảnh đất nổi danh với văn hóa ẩm thực bình dân độc đáo, "
                f"nơi đây chào đón bạn bằng hương vị thơm lừng của {specialties_str}. "
                f"{weather_phrase} "
                f"Hãy cùng thả chậm bước chân, ngắm nhìn nhịp sống rộn ràng và thưởng thức trọn vẹn hương vị tinh túy của nơi này nhé!"
            )

        suggested_voice = tts_service.get_voice_for_language(req.language_code)

        return AINarrationResponse(
            title=title,
            description=description,
            narration_text=narration,
            suggested_voice=suggested_voice,
            weather_context_applied=weather
        )


ai_service = AIService()
