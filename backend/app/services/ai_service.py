import logging
from typing import Optional
import httpx
from fastapi import HTTPException

import json
from app.core.config import settings
from app.schemas.ai import (
    AINarrationRequest,
    AINarrationResponse,
    POIAssistantRequest,
    POIAssistantResponse,
    AIRefineDescriptionRequest,
    AIRefineDescriptionResponse,
    AIMultilingualTranslateRequest,
    AIMultilingualTranslateResponse,
    MultilingualItem,
)
from app.services.tts_service import tts_service

logger = logging.getLogger("uvicorn")


def safe_parse_json(raw_text: str) -> dict:
    """Safely extracts and parses JSON even if wrapped in markdown fences, unescaped newlines or inner quotes."""
    import re
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    json_str = match.group(0) if match else cleaned

    try:
        return json.loads(json_str, strict=False)
    except Exception:
        pass

    try:
        fixed = re.sub(r"(?<!\\)\r?\n", " ", json_str)
        return json.loads(fixed, strict=False)
    except Exception:
        pass

    extracted = {}
    for key in ["title", "description", "narration_text", "name", "address", "category", "narration_script", "suggested_title", "refined_description"]:
        m = re.search(rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"', json_str)
        if m:
            extracted[key] = m.group(1).replace(r'\"', '"').replace(r'\n', '\n')
    return extracted


class AIService:
    @classmethod
    def get_gemini_models(cls) -> list:
        return [settings.GEMINI_MODEL]

    @classmethod
    async def generate_narration(cls, req: AINarrationRequest) -> AINarrationResponse:
        """
        Generates context-aware, tourist-friendly narration text using Google Gemini AI.
        Incorporates POI category, specialties, tone, and weather.
        """
        name = req.poi_name
        category = req.category
        weather = req.weather or "mát mẻ dễ chịu"
        specialties_str = ", ".join(req.specialties) if req.specialties else "các món ăn và nét văn hóa đặc trưng"
        suggested_voice = tts_service.get_voice_for_language(req.language_code)

        # 1. Try Google Gemini AI if API Key is configured
        if settings.GEMINI_API_KEY:
            try:
                lang_instruction = "bằng Tiếng Việt" if req.language_code.startswith("vi") else f"in language '{req.language_code}'"
                prompt = (
                    f"Bạn là một hướng dẫn viên du lịch số chuyên nghiệp và am hiểu sâu sắc về Quận 4, TP. Hồ Chí Minh.\n"
                    f"Hãy viết một bài thuyết minh âm thanh ngắn gọn, truyền cảm {lang_instruction} cho du khách đang đến thăm:\n"
                    f"- Địa điểm: {name}\n"
                    f"- Phân loại: {category}\n"
                    f"- Đặc sản / Nét nổi bật: {specialties_str}\n"
                    f"- Thời tiết hiện tại: {weather}\n"
                    f"- Tông điệu mong muốn: {req.tone or 'thân thiện, ấm cúng và hiếu khách'}\n\n"
                    f"Yêu cầu:\n"
                    f"1. Tiêu đề ngắn gọn (dưới 10 từ)\n"
                    f"2. Mô tả ngắn (1 câu)\n"
                    f"3. Lời thuyết minh chi tiết (khoảng 80-120 từ, văn phong tự nhiên để nghe trên tai nghe GPS, nhắc khéo đến thời tiết và khuyến khích trải nghiệm).\n\n"
                    f"QUAN TRỌNG: Chỉ trả về duy nhất JSON hợp lệ:\n"
                    f"{{\n"
                    f"  \"title\": \"Tiêu đề ngắn...\",\n"
                    f"  \"description\": \"Mô tả ngắn...\",\n"
                    f"  \"narration_text\": \"Lời thuyết minh đầy đủ 80-120 từ...\"\n"
                    f"}}"
                )

                for model_name in cls.get_gemini_models():
                    try:
                        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"

                        payload = {
                            "contents": [{
                                "parts": [{"text": prompt}]
                            }],
                            "generationConfig": {
                                "temperature": 0.5,
                                "maxOutputTokens": 2000,
                                "responseMimeType": "application/json"
                            }
                        }

                        async with httpx.AsyncClient(timeout=25.0) as client:
                            resp = await client.post(gemini_url, json=payload)
                            if resp.status_code == 200:
                                res_json = resp.json()
                                candidates = res_json.get("candidates", [])
                                if candidates and "content" in candidates[0]:
                                    parts = candidates[0]["content"].get("parts", [])
                                    if parts and "text" in parts[0]:
                                        full_text = parts[0]["text"].strip()
                                        parsed = safe_parse_json(full_text)

                                        return AINarrationResponse(
                                            title=parsed.get("title") or f"Khám phá {name}",
                                            description=parsed.get("description") or f"Điểm đến {category} đặc sắc tại Quận 4.",
                                            narration_text=parsed.get("narration_text") or full_text,
                                            suggested_voice=suggested_voice,
                                            weather_context_applied=weather
                                        )
                            else:
                                logger.warning(f"Gemini API ({model_name}) returned status {resp.status_code}: {resp.text[:200]}")
                    except Exception as ex:
                        logger.warning(f"Gemini narration error on {model_name}: {ex}")
            except Exception as ex:
                logger.warning(f"Failed to generate narration via Gemini AI: {ex}. Falling back to template.")

        raise HTTPException(502, "Dịch vụ AI chưa trả về kết quả hợp lệ. Vui lòng thử lại hoặc nhập nội dung thủ công.")

    @classmethod
    async def generate_poi_profile(cls, req: POIAssistantRequest) -> POIAssistantResponse:
        """
        AI-assisted POI profile generation using Google Gemini.
        Recognizes the restaurant or landmark name, and auto-generates:
        - Engaging 3-5 sentence description
        - Specific District 4 / HCMC address
        - Matching category
        - Tourist audio guide narration script
        - Key specialties/dishes
        - Approximate GPS coordinates
        """
        name = req.poi_name.strip()
        address_hint = req.address_hint or ""
        category_hint = req.category_hint or ""
        context = req.context or ""

        # 1. Attempt Gemini generation with fallback models on high demand / 503
        if settings.GEMINI_API_KEY:
            for model_name in cls.get_gemini_models():
                try:
                    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"

                    prompt = (
                        f"Bạn là chuyên gia am hiểu sâu sắc về địa lý, văn hóa, ẩm thực và du lịch tại Quận 4 cũng như TP. Hồ Chí Minh, Việt Nam.\n"
                        f"Người dùng đang thêm một địa điểm / quán ăn mới vào hệ thống bản đồ thuyết minh du lịch số có tên là: \"{name}\".\n"
                        f"Gợi ý địa chỉ: \"{address_hint}\". Gợi ý phân loại: \"{category_hint}\". Bối cảnh thêm: \"{context}\".\n\n"
                        f"Yêu cầu nhiệm vụ:\n"
                        f"1. Nhận diện chính xác quán ăn/địa điểm này (nếu là quán nổi tiếng ở Quận 4/Sài Gòn như Ốc Oanh, Ốc Đào, Phá Lấu Bò Dì Nủi, Chợ Xóm Chiếu, Bến Nhà Rồng, Cầu Mống, Cơm tấm, Hủ tiếu,... hãy cung cấp thông tin thực tế chuẩn xác nhất).\n"
                        f"2. Viết một đoạn văn mô tả (description) thật hấp dẫn, sinh động, giàu hình ảnh và cảm xúc (khoảng 3-5 câu), nêu bật phong cách, hương vị món ăn nổi tiếng nhất và trải nghiệm đáng nhớ.\n"
                        f"3. Cung cấp địa chỉ chuẩn xác tại Quận 4 (hoặc TP.HCM).\n"
                        f"4. Phân loại phù hợp nhất trong các nhóm: \"food_drink\", \"sightseeing\", \"historical\", \"culture\", \"shopping\", \"entertainment\".\n"
                        f"5. Viết một bài thuyết minh audio ngắn (narration_script, khoảng 80-120 từ) với lời chào du khách truyền cảm hứng.\n"
                        f"6. Liệt kê 3-5 món đặc sản / điểm độc đáo tiêu biểu (specialties).\n"
                        f"7. Ước lượng tọa độ GPS (latitude ~10.76xxx, longitude ~106.70xxx) gần đúng tại Quận 4.\n\n"
                        f"QUAN TRỌNG: Chỉ trả về duy nhất một chuỗi JSON hợp lệ (không có ký tự nào ngoài JSON):\n"
                        f"{{\n"
                        f"  \"name\": \"Tên chuẩn hóa\",\n"
                        f"  \"category\": \"food_drink\",\n"
                        f"  \"address\": \"Địa chỉ đầy đủ tại Quận 4, TP.HCM\",\n"
                        f"  \"description\": \"Đoạn mô tả 3-5 câu hấp dẫn...\",\n"
                        f"  \"narration_script\": \"Lời dẫn thuyết minh audio 80-120 từ...\",\n"
                        f"  \"specialties\": [\"Món 1\", \"Món 2\", \"Món 3\"],\n"
                        f"  \"latitude\": 10.7635,\n"
                        f"  \"longitude\": 106.7042\n"
                        f"}}"
                    )

                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.3,
                            "maxOutputTokens": 2500,
                            "responseMimeType": "application/json"
                        }
                    }

                    async with httpx.AsyncClient(timeout=25.0) as client:
                        resp = await client.post(gemini_url, json=payload)
                        if resp.status_code == 200:
                            res_json = resp.json()
                            candidates = res_json.get("candidates", [])
                            if candidates and "content" in candidates[0]:
                                parts = candidates[0]["content"].get("parts", [])
                                if parts and "text" in parts[0]:
                                    raw_text = parts[0]["text"].strip()
                                    parsed = safe_parse_json(raw_text)

                                    # Map category to standard supported category
                                    raw_cat = (parsed.get("category") or "food_drink").lower()
                                    if any(k in raw_cat for k in ["food", "ăn", "ẩm thực", "ốc", "uống", "drink"]):
                                        final_cat = "food_drink"
                                    elif any(k in raw_cat for k in ["lịch sử", "historic", "di tích"]):
                                        final_cat = "historical"
                                    elif any(k in raw_cat for k in ["văn hóa", "culture", "chùa", "nhà thờ"]):
                                        final_cat = "culture"
                                    elif any(k in raw_cat for k in ["mua sắm", "shop", "chợ"]):
                                        final_cat = "shopping"
                                    elif any(k in raw_cat for k in ["giải trí", "entertainment"]):
                                        final_cat = "entertainment"
                                    else:
                                        final_cat = "sightseeing"

                                    # Coordinates must be confirmed on the map by the editor.
                                    parsed_lat, parsed_lng = None, None

                                    return POIAssistantResponse(
                                        name=parsed.get("name") or name,
                                        category=final_cat,
                                        address=parsed.get("address") or address_hint or "Quận 4, TP. Hồ Chí Minh",
                                        description=parsed.get("description") or f"{name} là điểm đến ẩm thực và văn hóa đặc sắc tại Quận 4.",
                                        narration_script=parsed.get("narration_script") or f"Chào mừng bạn đến với {name} tại Quận 4!",
                                        specialties=parsed.get("specialties") or ["Món ngon đặc sản Quận 4"],
                                        latitude=parsed_lat,
                                        longitude=parsed_lng,
                                        confidence="requires_review"
                                    )
                        else:
                            logger.warning(f"Gemini API ({model_name}) returned status {resp.status_code}: {resp.text[:120]}. Trying next model if available...")
                except Exception as e:
                    logger.warning(f"Gemini POI profile error on {model_name}: {e}. Trying next model...")


        raise HTTPException(502, "Dịch vụ AI chưa trả về kết quả hợp lệ. Vui lòng thử lại hoặc nhập nội dung thủ công.")

    @classmethod
    async def refine_poi_description(cls, req: AIRefineDescriptionRequest) -> AIRefineDescriptionResponse:
        """
        Refines, polishes, or enriches a POI description into an enticing, vivid 3-5 sentence tourist narrative.
        Can adjust according to specified tone ('cuốn hút', 'lịch sử', 'hài hước', 'ngắn gọn').
        """
        name = req.poi_name.strip()
        current_desc = req.current_description.strip() if req.current_description else ""
        category = req.category or "food_drink"
        tone = req.tone or "cuốn hút, sinh động và giàu cảm xúc du lịch"

        if settings.GEMINI_API_KEY:
            for model_name in cls.get_gemini_models():
                try:
                    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"
                    prompt = (
                        f"Bạn là một chuyên gia biên tập nội dung du lịch và ẩm thực chuyên nghiệp, am hiểu sâu sắc về Quận 4, TP. Hồ Chí Minh.\n"
                        f"Hãy giúp quản trị viên tối ưu hóa, nâng cấp hoặc viết mới đoạn mô tả cho địa điểm du lịch sau:\n"
                        f"- Tên địa điểm: {name}\n"
                        f"- Danh mục: {category}\n"
                        f"- Địa chỉ / Gợi ý: {req.address or 'Quận 4, TP. Hồ Chí Minh'}\n"
                        f"- Nội dung hiện tại (nếu có): \"{current_desc}\"\n"
                        f"- Tông điệu mong muốn: {tone}\n\n"
                        f"Yêu cầu:\n"
                        f"1. Viết lại một đoạn mô tả du lịch (refined_description) dài 3-5 câu thật hấp dẫn, truyền cảm, làm nổi bật hương vị món ăn hoặc giá trị văn hóa lịch sử độc đáo tại Quận 4.\n"
                        f"2. Gợi ý 1 tiêu đề ngắn (suggested_title) dưới 10 từ.\n"
                        f"3. Trích xuất 3-4 điểm nổi bật / món ngon tiêu biểu (highlights).\n"
                        f"4. Viết 1 câu kịch bản dẫn nhập audio guide (narration_script) tự nhiên, thân thiện.\n\n"
                        f"QUAN TRỌNG: Chỉ trả về duy nhất chuỗi JSON hợp lệ với cấu trúc sau:\n"
                        f"{{\n"
                        f"  \"suggested_title\": \"...\",\n"
                        f"  \"refined_description\": \"...\",\n"
                        f"  \"highlights\": [\"Điểm 1\", \"Điểm 2\", \"Điểm 3\"],\n"
                        f"  \"narration_script\": \"...\"\n"
                        f"}}"
                    )

                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.4,
                            "maxOutputTokens": 2000,
                            "responseMimeType": "application/json"
                        }
                    }

                    async with httpx.AsyncClient(timeout=25.0) as client:
                        resp = await client.post(gemini_url, json=payload)
                        if resp.status_code == 200:
                            res_json = resp.json()
                            candidates = res_json.get("candidates", [])
                            if candidates and "content" in candidates[0]:
                                parts = candidates[0]["content"].get("parts", [])
                                if parts and "text" in parts[0]:
                                    raw_text = parts[0]["text"].strip()
                                    parsed = safe_parse_json(raw_text)

                                    return AIRefineDescriptionResponse(
                                        poi_name=name,
                                        refined_description=parsed.get("refined_description") or current_desc,
                                        suggested_title=parsed.get("suggested_title") or f"Khám phá {name}",
                                        highlights=parsed.get("highlights") or ["Đặc sản nổi tiếng", "Không gian gần gũi"],
                                        narration_script=parsed.get("narration_script") or f"Chào mừng bạn đến với {name} tại Quận 4."
                                    )
                except Exception as ex:
                    logger.warning(f"Failed to refine description with {model_name}: {ex}")

        raise HTTPException(502, "Dịch vụ AI chưa trả về kết quả hợp lệ. Vui lòng thử lại hoặc nhập nội dung thủ công.")

    @classmethod
    async def multilingual_cultural_translate(cls, req: AIMultilingualTranslateRequest) -> AIMultilingualTranslateResponse:
        """
        Translates POI name and description into 6 languages (vi, en, fr, ja, ko, zh) using Google Gemini AI,
        preserving Vietnamese culinary nuance (street food names, District 4 landmarks) instead of literal word translation.
        """
        name = req.poi_name.strip()
        desc = req.description.strip()
        category = req.category or "food_drink"

        if settings.GEMINI_API_KEY:
            for model_name in cls.get_gemini_models():
                try:
                    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"
                    prompt = (
                        f"Bạn là một chuyên gia dịch thuật du lịch và bản địa hóa đa ngôn ngữ chuyên nghiệp.\n"
                        f"Hãy dịch thông tin địa điểm du lịch/ẩm thực tại Quận 4, TP. Hồ Chí Minh sang 6 ngôn ngữ:\n"
                        f"- Tiếng Việt (vi)\n"
                        f"- Tiếng Anh (en)\n"
                        f"- Tiếng Pháp (fr)\n"
                        f"- Tiếng Nhật (ja)\n"
                        f"- Tiếng Hàn (ko)\n"
                        f"- Tiếng Trung giản thể (zh)\n\n"
                        f"Thông tin nguồn:\n"
                        f"- Tên: {name}\n"
                        f"- Phân loại: {category}\n"
                        f"- Mô tả: {desc}\n\n"
                        f"Yêu cầu dịch thuật:\n"
                        f"1. Với món ăn đặc trưng Việt Nam (như 'Ốc', 'Phá lấu', 'Bánh tráng nướng', 'Cơm tấm', 'Hủ tiếu'): Giữ nguyên tên phiên âm tiếng Việt và thêm phần giải thích món ăn ngắn gọn, tự nhiên bằng ngôn ngữ đích để du khách quốc tế hiểu rõ.\n"
                        f"2. Văn phong mô tả hấp dẫn, lôi cuốn theo phong cách hướng dẫn viên du lịch chuyên nghiệp.\n"
                        f"3. Trả về DUY NHẤT một JSON hợp lệ với cấu trúc:\n"
                        f"{{\n"
                        f"  \"vi\": {{\"name\": \"...\", \"description\": \"...\"}},\n"
                        f"  \"en\": {{\"name\": \"...\", \"description\": \"...\"}},\n"
                        f"  \"fr\": {{\"name\": \"...\", \"description\": \"...\"}},\n"
                        f"  \"ja\": {{\"name\": \"...\", \"description\": \"...\"}},\n"
                        f"  \"ko\": {{\"name\": \"...\", \"description\": \"...\"}},\n"
                        f"  \"zh\": {{\"name\": \"...\", \"description\": \"...\"}}\n"
                        f"}}"
                    )

                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.2,
                            "maxOutputTokens": 3000,
                            "responseMimeType": "application/json"
                        }
                    }

                    async with httpx.AsyncClient(timeout=25.0) as client:
                        resp = await client.post(gemini_url, json=payload)
                        if resp.status_code == 200:
                            res_json = resp.json()
                            candidates = res_json.get("candidates", [])
                            if candidates and "content" in candidates[0]:
                                parts = candidates[0]["content"].get("parts", [])
                                if parts and "text" in parts[0]:
                                    raw_text = parts[0]["text"].strip()
                                    parsed = safe_parse_json(raw_text)

                                    translations = {}
                                    for l_code in ["vi", "en", "fr", "ja", "ko", "zh"]:
                                        item = parsed.get(l_code, {})
                                        translations[l_code] = MultilingualItem(
                                            name=item.get("name") or name,
                                            description=item.get("description") or desc
                                        )

                                    return AIMultilingualTranslateResponse(
                                        poi_id=req.poi_id,
                                        translations=translations
                                    )
                except Exception as ex:
                    logger.warning(f"Failed Gemini multilingual translation with {model_name}: {ex}")

        raise HTTPException(502, "Dịch vụ AI chưa trả về kết quả hợp lệ. Vui lòng thử lại hoặc nhập nội dung thủ công.")


ai_service = AIService()
