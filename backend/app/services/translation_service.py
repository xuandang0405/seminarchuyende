"""Multi-language Translation & Google TTS Synchronization Service.

Provides:
1. Automated translation into 6 supported languages: Vietnamese (vi), English (en), French (fr), Japanese (ja), Korean (ko), Chinese (zh).
2. Curated District 4 POI dictionary for high fidelity, culturally authentic descriptions.
3. Automated multi-language Google TTS (gTTS) generation for each language.
4. Database synchronization for both `pois` and `poi_localizations` collections.
"""

import os
import re
import asyncio
import logging
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from gtts import gTTS

from app.core.config import settings

logger = logging.getLogger("uvicorn")

SUPPORTED_LANGUAGES = ["vi", "en", "fr", "ja", "ko", "zh"]

# Language display metadata
LANGUAGE_INFO = {
    "vi": {"label": "Tiếng Việt", "flag": "🇻🇳", "gtts_code": "vi"},
    "en": {"label": "English", "flag": "🇬🇧", "gtts_code": "en"},
    "fr": {"label": "Français", "flag": "🇫🇷", "gtts_code": "fr"},
    "ja": {"label": "日本語", "flag": "🇯🇵", "gtts_code": "ja"},
    "ko": {"label": "한국어", "flag": "🇰🇷", "gtts_code": "ko"},
    "zh": {"label": "中文", "flag": "🇨🇳", "gtts_code": "zh"},
}

# Curated High-Quality District 4 Knowledge Base
DISTRICT_4_CURATED_POIS = {
    "poi_ben_nha_rong": {
        "vi": {
            "name": "Bến Nhà Rồng - Bảo Tàng Hồ Chí Minh",
            "description": "Di tích lịch sử văn hóa tiêu biểu của Quận 4 và TP.HCM, nơi Bác Hồ ra đi tìm đường cứu nước năm 1911. Kiến trúc kết hợp độc đáo giữa nét cổ kính Á Đông và kiến trúc Pháp bên bờ sông Sài Gòn."
        },
        "en": {
            "name": "Dragon Wharf - Ho Chi Minh Museum",
            "description": "Iconic historical landmark of District 4 and Ho Chi Minh City, where President Ho Chi Minh departed in 1911 to seek national liberation. Features distinctive French-colonial architecture alongside the Saigon River."
        },
        "fr": {
            "name": "Quai du Dragon - Musée Ho Chi Minh",
            "description": "Monument historique emblématique du 4e arrondissement et d'Hô Chi Minh-Ville, d'où le président Hô Chi Minh est parti en 1911 pour trouver la voie du salut national. Architecture coloniale française au bord de la rivière Saïgon."
        },
        "ja": {
            "name": "ドラゴン埠頭 - ホーチミン博物館",
            "description": "1911年にホー・チ・ミン主席が救国の道を探すために出発した、第4区およびホーチミン市を代表する歴史的建造物です。サイゴン川沿いに建つ東洋とフランスの融合建築です。"
        },
        "ko": {
            "name": "드래곤 부두 - 호치민 박물관",
            "description": "1911년 호치민 주석이 구국의 길을 찾기 위해 출항한 역사적인 장소이자 4군과 호치민시의 상징적인 문화유적지입니다. 사이공 강변에 위치한 독특한 프랑스 식민지 양식의 건축물입니다."
        },
        "zh": {
            "name": "龙屋港 - 胡志明博物馆",
            "description": "胡志明市第四郡标志性历史文化遗迹，1911年胡志明主席在此启程寻求救国道路。矗立于西贡河畔，融汇了独特的法式殖民地与东方古典建筑风格。"
        }
    },
    "poi_pho_oc_vinh_khanh": {
        "vi": {
            "name": "Phố Ẩm Thực Vĩnh Khánh",
            "description": "Con phố ẩm thực đêm sôi động bậc nhất Quận 4 với hàng chục quán ốc, hải sản tươi sống và không khí ẩm thực đường phố nhộn nhịp đậm chất Sài Gòn."
        },
        "en": {
            "name": "Vinh Khanh Seafood & Food Street",
            "description": "The most vibrant night food street in District 4, famous for sizzling snails, fresh seafood, and energetic Saigon street culinary culture."
        },
        "fr": {
            "name": "Rue Gastronomique de Vinh Khanh",
            "description": "La rue nocturne la plus animée du 4e arrondissement, réputée pour ses escargots de mer, ses fruits de mer frais et son ambiance populaire typique de Saïgon."
        },
        "ja": {
            "name": "ビンカン屋台通り（シーフード通り）",
            "description": "新鮮な巻貝や魚介類料理で有名な第4区屈指のナイトグルメストリート。活気あふれるサイゴンの夜の食文化を満喫できます。"
        },
        "ko": {
            "name": "빈칸 야간 해산물 거리",
            "description": "신선한 우렁이, 조개 및 해산물 요리로 유명한 4군 최고의 먹거리 야시장 거리로, 활기찬 사이공의 길거리 음식 문화를 즐길 수 있습니다."
        },
        "zh": {
            "name": "永庆海鲜美食街",
            "description": "第四郡最具活力的夜市美食街，以各式鲜美炒螺、海鲜烧烤和地道的西贡市井饮食氛围而闻名遐迩。"
        }
    },
    "poi_cho_xom_chieu": {
        "vi": {
            "name": "Chợ Xóm Chiếu (Chợ 200)",
            "description": "Thiên đường ẩm thực dân dã truyền thống của người dân Quận 4, nổi tiếng với các món chè, bánh xèo, phá lấu và các món ăn vặt đặc sắc lâu đời."
        },
        "en": {
            "name": "Xom Chieu Market (Market 200)",
            "description": "Traditional culinary paradise of District 4 locals, celebrated for its dessert sweet soups, Vietnamese savory pancakes, phá lấu, and authentic vintage snacks."
        },
        "fr": {
            "name": "Marché de Xom Chieu (Marché 200)",
            "description": "Paradis gastronomique traditionnel du 4e arrondissement, réputé pour ses soupes douces chè, crêpes vietnamiennes bánh xèo et spécialités populaires locales."
        },
        "ja": {
            "name": "ソムチエウ市場（200市場）",
            "description": "第4区の地元の人々に愛される伝統的なローカルグルメ天国。チェーやバインセオ、パウラウなど本場のベトナム軽食が揃います。"
        },
        "ko": {
            "name": "솜찌우 전통 시장 (200 시장)",
            "description": "4군 주민들의 전통적인 길거리 미식 천국으로, 달콤한 째(Chè), 반세오, 파러우 등 오랜 역사를 자랑하는 베트남 전통 간식거리로 가득합니다."
        },
        "zh": {
            "name": "广照街市 (200市集)",
            "description": "第四郡当地人最爱的传统市井美食天堂，以地道糖水甜品、越式煎饼、牛杂及数十种老字号风味小吃闻名。"
        }
    },
    "poi_cau_mong": {
        "vi": {
            "name": "Cầu Mống (Cầu Xanh Bến Vân Đồn)",
            "description": "Cây cầu cổ hơn 100 năm tuổi bắc qua kênh Bến Nghé nối Quận 1 và Quận 4, do công ty kiến trúc Eiffel của Pháp thiết kế với màu xanh ngọc lam đặc trưng."
        },
        "en": {
            "name": "Mong Bridge (Rainbow Bridge)",
            "description": "Century-old historical pedestrian bridge spanning the Ben Nghe Canal between District 1 and District 4, designed by the Eiffel architectural firm in iconic turquoise."
        },
        "fr": {
            "name": "Pont des Messageries (Pont Mong)",
            "description": "Pont piétonnier centenaire enjambant le canal de Ben Nghe entre le 1er et le 4e arrondissement, conçu par les ateliers Eiffel avec sa couleur turquoise emblématique."
        },
        "ja": {
            "name": "モン橋（虹の橋）",
            "description": "エッフェル社によって設計された100年以上の歴史を誇る歩道橋。ベンゲー運河に架かり、第1区と第4区を結ぶ鮮やかなターコイズブルーの景観です。"
        },
        "ko": {
            "name": "몽 다리 (무지개 다리)",
            "description": "1군과 4군을 잇는 벤응에 운하를 가로지르는 100년 역사의 유서 깊은 보행자 다리로, 에펠사가 설계한 특유의 청록색 철골 구조물이 돋보입니다."
        },
        "zh": {
            "name": "芒桥 (彩虹古桥)",
            "description": "横跨滨义运河、连接第一郡与第四郡的百年历史古桥，由法国埃菲尔公司设计，拥有标志性的蓝绿色钢结构建筑风貌。"
        }
    },
    "poi_chua_giac_nguyen": {
        "vi": {
            "name": "Chùa Giác Nguyên",
            "description": "Ngôi cổ tự thanh tịnh tọa lạc tại trung tâm Quận 4, là điểm sinh hoạt Phật giáo tâm linh quan trọng với kiến trúc trang nghiêm và không gian tĩnh lặng."
        },
        "en": {
            "name": "Giac Nguyen Pagoda",
            "description": "A serene historical Buddhist pagoda in the heart of District 4, serving as a peaceful spiritual sanctuary with venerable Buddhist architecture."
        },
        "fr": {
            "name": "Pagode Giac Nguyen",
            "description": "Pagode bouddhiste sereine au cœur du 4e arrondissement, offrant un sanctuaire spirituel paisible à l'architecture traditionnelle remarquable."
        },
        "ja": {
            "name": "ジャックグエン寺院",
            "description": "第4区の中心部に位置する歴史ある仏教寺院。厳かな伝統建築と静寂に包まれた心安らぐ祈りの空間が広がっています。"
        },
        "ko": {
            "name": "각원사 (Giac Nguyen Pagoda)",
            "description": "4군 중심부에 자리 잡은 고요한 전통 불교 사찰로, 장엄한 건축 양식과 평화로운 참선 공간을 갖춘 소중한 영적 안식처입니다."
        },
        "zh": {
            "name": "觉元寺",
            "description": "坐落于第四郡市中心的古朴宁静佛寺，香火鼎盛，拥有庄严典雅的传统佛教建筑与令人沉心静气的禅意空间。"
        }
    },
    "poi_banh_xeo": {
        "vi": {
            "name": "Quán Bánh Xèo Bà Hai Quận 4",
            "description": "Quán bánh xèo truyền thống giòn rụm với tôm thịt đầy đặn, ăn kèm rổ rau rừng thanh mát và nước mắm chua ngọt pha theo công thức gia truyền lâu năm."
        },
        "en": {
            "name": "Ba Hai Crispy Vietnamese Pancake",
            "description": "Authentic crispy savory Vietnamese crepe stuffed with plump prawns and pork, served with a lush basket of wild fresh herbs and heirloom sweet-sour dipping sauce."
        },
        "fr": {
            "name": "Bánh Xèo Traditionnel Ba Hai",
            "description": "Crêpe vietnamienne croustillante garnie de crevettes et de porc savoureux, accompagnée d'herbes aromatiques fraîches et d'une sauce nuoc-mâm artisanale."
        },
        "ja": {
            "name": "バーハイ・バインセオ専門店",
            "description": "エビと豚肉がたっぷり入ったサクサク食感の本格ベトナム風お好み焼き。たっぷりの新鮮な香草と秘伝の甘酢タレでいただきます。"
        },
        "ko": {
            "name": "바하이 바삭한 반세오 맛집",
            "description": "새우와 돼지고기가 듬뿍 들어간 바삭바삭한 정통 베트남식 부침개로, 신선한 쌈 야채와 오랜 전통의 새콤달콤한 느억맘 소스와 함께 즐깁니다."
        },
        "zh": {
            "name": "二奶越式香脆煎饼",
            "description": "传统地道的第四郡脆皮越南煎饼，内馅饱满包裹鲜虾与五花肉，搭配新鲜爽口的生菜香草与秘制酸甜鱼露蘸汁。"
        }
    },
    "poi_hem_200_xom_chieu": {
        "vi": {
            "name": "Hẻm Ẩm Thực 200 Xóm Chiếu",
            "description": "Con hẻm ẩm thực nức tiếng Sài Gòn quy tụ hàng trăm món ăn đường phố hấp dẫn: phá lấu, chuối nếp nướng, bột chiên, ốc và sinh tố trái cây."
        },
        "en": {
            "name": "Alley 200 Xom Chieu Food Haven",
            "description": "Saigon's famous street food alley packed with vibrant food stalls offering phá lấu, grilled sticky rice bananas, pan-fried rice cakes, and tropical smoothies."
        },
        "fr": {
            "name": "Allée Gastronomique 200 Xom Chieu",
            "description": "Ruelle culinaire réputée de Saïgon regroupant des dizaines d'étals proposant phá lấu, bananes grillées au riz gluant et spécialités de rue."
        },
        "ja": {
            "name": "ソムチエウ200路地グルメ街",
            "description": "サイゴン随一の路地裏グルメスポット。名物のパウラウ、焼きバナナ餅、ボッチエンなど魅力的なローカル屋台が軒を連ねます。"
        },
        "ko": {
            "name": "솜찌우 200 미식 골목",
            "description": "사이공에서 가장 유명한 먹자골목 중 하나로 파러우, 바나나 찹쌀구이, 봇찌엔 등 다채로운 길거리 간식이 끝없이 펼쳐집니다."
        },
        "zh": {
            "name": "广照200美食巷",
            "description": "名扬全西贡的街头小吃弄堂，汇集了卤牛杂、烤糯米芭蕉、煎米糕、螺肉及新鲜热带水果冰沙等数百种地道风味。"
        }
    },
    "poi_ben_van_don": {
        "vi": {
            "name": "Công Viên Bờ Sông Bến Vân Đồn",
            "description": "Cung đường đi bộ ven sông thơ mộng nhìn sang trung tâm Quận 1, nơi lý tưởng để hóng gió, ngắm hoàng hôn và chiêm ngưỡng vẻ đẹp lung linh của thành phố về đêm."
        },
        "en": {
            "name": "Ben Van Don Riverside Promenade",
            "description": "Picturesque riverside parkway facing District 1 skyline, perfect for breezy strolls, sunset views, and admiring Saigon's sparkling nightlife."
        },
        "fr": {
            "name": "Promenade Fluviale de Ben Van Don",
            "description": "Promenade pittoresque au bord de l'eau face aux gratte-ciel du 1er arrondissement, idéale pour contempler le coucher de soleil et les illuminations de la ville."
        },
        "ja": {
            "name": "ベンヴァンドン川沿いプロムナード",
            "description": "第1区の高層ビル群を一望できる風光明媚なリバーサイド遊歩道。夕暮れの涼風と美しいサイゴンの夜景を楽しめる憩いの場です。"
        },
        "ko": {
            "name": "벤반돈 강변 산책로 공원",
            "description": "1군의 스카이라인을 마주하는 운치 있는 강변 산책로로, 시원한 강바람을 맞으며 석양과 화려한 도심 야경을 감상하기에 가장 좋습니다."
        },
        "zh": {
            "name": "滨云屯江畔休闲公园",
            "description": "隔河眺望第一郡繁华摩天大楼天际线的滨江林荫步道，微风拂面，是散步休闲、观赏夕阳晚霞和西贡璀璨夜景的绝佳去处。"
        }
    },
    "poi_nha_tho_xom_chieu": {
        "vi": {
            "name": "Nhà Thờ Giáo Xứ Xóm Chiếu",
            "description": "Công trình tôn giáo cổ kính được xây dựng từ thế kỷ 19 với tháp chuông thanh thoát, là trung tâm sinh hoạt cộng đồng lâu đời của giáo dân Quận 4."
        },
        "en": {
            "name": "Xom Chieu Parish Church",
            "description": "Historic Catholic church built in the 19th century with graceful belfries, serving as a cherished cultural and spiritual anchor in District 4."
        },
        "fr": {
            "name": "Église Paroissiale de Xom Chieu",
            "description": "Église catholique historique érigée au XIXe siècle avec son élégant clocher, cœur spirituel et communautaire séculaire du 4e arrondissement."
        },
        "ja": {
            "name": "ソムチエウ教会",
            "description": "19世紀に建立された歴史あるカトリック教会。優美な鐘楼を持ち、第4区の人々の心の拠り所として親しまれています。"
        },
        "ko": {
            "name": "솜찌우 가톨릭 성당",
            "description": "19세기에 건립된 우아한 종탑을 가진 유서 깊은 성당으로, 4군 주민들의 오랜 역사와 따뜻한 공동체 신앙의 중심지입니다."
        },
        "zh": {
            "name": "广照天主堂",
            "description": "始建于19世纪的古老天主教堂，拥有典雅庄严的钟楼，是第四郡教友与当地社区悠久的文化精神地标。"
        }
    },
    "poi_cong_vien_tan_thuan": {
        "vi": {
            "name": "Công Viên Cầu Tân Thuận",
            "description": "Khuôn viên xanh mát nối liền Quận 4 và Quận 7, không gian tập thể dục và dạo mát thoáng đãng bên dòng kênh Tẻ thanh bình."
        },
        "en": {
            "name": "Tan Thuan Bridge Riverside Park",
            "description": "Lush green recreational area connecting District 4 and District 7, providing open outdoor exercise and leisure spaces along the peaceful Te canal."
        },
        "fr": {
            "name": "Parc du Pont Tan Thuan",
            "description": "Espace vert verdoyant reliant le 4e et le 7e arrondissement, offrant un cadre aéré pour le sport et la détente le long du canal Te."
        },
        "ja": {
            "name": "タントゥアン橋親水公園",
            "description": "第4区と第7区を結ぶ緑豊かな水辺の公園。テ運河沿いの爽やかな風の中で運動や散策を楽しめる憩いのエリアです。"
        },
        "ko": {
            "name": "탄투안 대교 수변 공원",
            "description": "4군과 7군을 연결하는 푸른 녹지 수변 공원으로, 평화로운 떼(Te) 운하를 따라 산책과 야외 운동을 즐길 수 있는 힐링 공간입니다."
        },
        "zh": {
            "name": "新顺桥滨水绿化公园",
            "description": "连接第四郡与第七郡的绿树成荫滨水休闲公园，依傍宁静的小运河，是户外运动、漫步休闲与放松身心的天然氧吧。"
        }
    }
}


MYMEMORY_LANG_MAP = {
    "en": "en-GB",
    "fr": "fr-FR",
    "ja": "ja-JP",
    "ko": "ko-KR",
    "zh": "zh-CN",
}


class TranslationService:
    def __init__(self):
        self.audio_dir = os.path.join(settings.MEDIA_STORAGE_DIR, "audio")
        os.makedirs(self.audio_dir, exist_ok=True)
        self._cache: Dict[str, str] = {}

    def _find_curated(self, query_id_or_name: str) -> Optional[Dict[str, Dict[str, str]]]:
        """Finds curated translations by POI ID or name keyword."""
        q = str(query_id_or_name or "").lower().strip()
        # Direct key match
        if q in DISTRICT_4_CURATED_POIS:
            return DISTRICT_4_CURATED_POIS[q]

        # Match by name keywords
        for key, trans in DISTRICT_4_CURATED_POIS.items():
            vi_name = trans.get("vi", {}).get("name", "").lower()
            if q in key or q in vi_name or vi_name in q:
                return trans
            if "nhà rồng" in q and "ben_nha_rong" in key:
                return trans
            if "vĩnh khánh" in q and "vinh_khanh" in key:
                return trans
            if ("xóm chiếu" in q or "chợ 200" in q) and "cho_xom_chieu" in key:
                return trans
            if "cầu mống" in q and "cau_mong" in key:
                return trans
            if "giác nguyên" in q and "giac_nguyen" in key:
                return trans
            if "bánh xèo" in q and "banh_xeo" in key:
                return trans
            if "bến vân đồn" in q and "ben_van_don" in key:
                return trans
            if "tân thuận" in q and "tan_thuan" in key:
                return trans
        return None

    async def translate_text(self, text: str, target_lang: str) -> str:
        """Translates arbitrary text into target language using multi-tier engines:
        1. In-memory cache lookup.
        2. MyMemoryTranslator (authentic native Japanese/Korean/Chinese/French/English characters).
        3. GoogleTranslator (secondary online engine).
        4. Clean fallback.
        """
        if not text or not text.strip():
            return ""
        if target_lang == "vi":
            return text

        cache_key = f"{text.strip()}::{target_lang}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Tier 1: MyMemoryTranslator
        try:
            from deep_translator import MyMemoryTranslator
            target_code = MYMEMORY_LANG_MAP.get(target_lang, target_lang)

            def _translate_mymemory():
                res = MyMemoryTranslator(source="vi-VN", target=target_code).translate(text)
                if res and "MYMEMORY WARNING" not in res and len(res.strip()) > 0:
                    return res.strip()
                return None

            result = await asyncio.to_thread(_translate_mymemory)
            if result:
                self._cache[cache_key] = result
                return result
        except Exception as e:
            logger.warning(f"MyMemoryTranslator error for '{text[:25]}...' ({target_lang}): {e}")

        # Tier 2: GoogleTranslator
        try:
            from deep_translator import GoogleTranslator
            g_lang = LANGUAGE_INFO.get(target_lang, {}).get("gtts_code", target_lang)
            if g_lang in ("zh", "zh-CN", "zh-TW"):
                g_lang = "zh-CN"

            def _translate_google():
                res = GoogleTranslator(source="auto", target=g_lang).translate(text)
                if res and len(res.strip()) > 0:
                    return res.strip()
                return None

            result = await asyncio.to_thread(_translate_google)
            if result:
                self._cache[cache_key] = result
                return result
        except Exception as e:
            logger.warning(f"GoogleTranslator error for '{text[:25]}...' ({target_lang}): {e}")

        return text

    async def get_or_create_translations(
        self,
        poi_id: str,
        name: str,
        description: str
    ) -> Dict[str, Dict[str, str]]:
        """Produces translations for all 6 languages (vi, en, fr, ja, ko, zh)."""
        # 1. Check curated database first
        curated = self._find_curated(poi_id) or self._find_curated(name)
        if curated:
            result = {}
            for lang in SUPPORTED_LANGUAGES:
                if lang in curated:
                    result[lang] = curated[lang]
                else:
                    result[lang] = {
                        "name": await self.translate_text(curated["vi"]["name"], lang),
                        "description": await self.translate_text(curated["vi"]["description"], lang),
                    }
            return result

        # 2. For custom POI, translate dynamically
        translations = {
            "vi": {"name": name, "description": description}
        }

        for lang in ["en", "fr", "ja", "ko", "zh"]:
            trans_name = await self.translate_text(name, lang)
            trans_desc = await self.translate_text(description, lang)
            translations[lang] = {
                "name": trans_name or name,
                "description": trans_desc or description
            }

        return translations

    async def generate_tts_for_poi(
        self,
        poi_id: str,
        translations: Dict[str, Dict[str, str]]
    ) -> Dict[str, Dict[str, Any]]:
        """Generates Google TTS (gTTS) audio MP3 files for all 6 languages."""
        audio_results = {}

        for lang in SUPPORTED_LANGUAGES:
            item = translations.get(lang, {})
            raw_title = item.get("name", "")
            raw_desc = item.get("description", "")
            # Strip any legacy bracket tags like [EN], [JA], [KO], [ZH]
            clean_title = re.sub(r"^\[[A-Za-z]{2,3}\]\s*", "", raw_title).strip()
            clean_desc = re.sub(r"^\[[A-Za-z]{2,3}\]\s*", "", raw_desc).strip()
            text_to_speak = f"{clean_title}. {clean_desc}".strip()
            if not text_to_speak:
                text_to_speak = f"Địa điểm {poi_id}"

            gtts_lang = LANGUAGE_INFO[lang]["gtts_code"]
            filename = f"{poi_id}_{lang}.mp3"
            file_path = os.path.join(self.audio_dir, filename)
            storage_key = f"audio/{filename}"
            audio_url = f"/storage/{storage_key}"

            try:
                def _synthesize(text=text_to_speak, lang_code=gtts_lang, path=file_path):
                    tts = gTTS(text=text, lang=lang_code, slow=False)
                    tts.save(path)

                await asyncio.to_thread(_synthesize)
                file_size = os.path.getsize(file_path)
                duration_ms = max(int((file_size / 4000.0) * 1000), 4000)

                audio_results[lang] = {
                    "audio_url": audio_url,
                    "audio_storage_key": storage_key,
                    "audio_duration_ms": duration_ms,
                    "file_size": file_size,
                    "status": "ready"
                }
                logger.info(f"Generated Google TTS audio for POI {poi_id} in {lang}: {file_path}")
            except Exception as e:
                logger.error(f"Failed to generate gTTS for {poi_id}_{lang}: {e}")
                audio_results[lang] = {
                    "audio_url": f"/storage/audio/{poi_id}_vi.mp3",
                    "audio_storage_key": f"audio/{poi_id}_vi.mp3",
                    "audio_duration_ms": 10000,
                    "status": "fallback"
                }

        return audio_results

    async def sync_poi_multilingual(
        self,
        poi_id: str,
        name: str,
        description: str,
        db: Any
    ) -> Dict[str, Any]:
        """Complete workflow:
        1. Translates name & description into 6 languages.
        2. Generates Google TTS audio MP3 for all 6 languages.
        3. Saves translations & audio URLs to MongoDB `pois` and `poi_localizations`.
        """
        now = datetime.now(timezone.utc)
        translations_text = await self.get_or_create_translations(poi_id, name, description)
        audio_map = await self.generate_tts_for_poi(poi_id, translations_text)

        # Assemble unified multilingual payload
        translations_doc = {}
        for lang in SUPPORTED_LANGUAGES:
            t = translations_text[lang]
            a = audio_map.get(lang, {})
            translations_doc[lang] = {
                "lang": lang,
                "name": t["name"],
                "title": t["name"],
                "description": t["description"],
                "audio_url": a.get("audio_url", f"/storage/audio/{poi_id}_{lang}.mp3"),
                "audio_storage_key": a.get("audio_storage_key"),
                "audio_duration_ms": a.get("audio_duration_ms", 12000),
                "audio_status": a.get("status", "ready"),
                "updated_at": now.isoformat(),
            }

        # 1. Update POI collection document
        from app.repositories.poi_repo import poi_repo

        vi_data = translations_doc["vi"]
        poi_update = {
            "name": vi_data["name"],
            "description": vi_data["description"],
            "audio_url": vi_data["audio_url"],
            "audio_duration_ms": vi_data["audio_duration_ms"],
            "audio_status": "ready",
            "translations": translations_doc,
            "published_contents": translations_doc,
            "updated_at": now,
        }

        try:
            await poi_repo.collection.update_one(
                {"_id": poi_id},
                {"$set": poi_update},
                upsert=False
            )
        except Exception as e:
            logger.warning(f"Could not update poi_repo.collection for {poi_id}: {e}")

        # Also update by slug if original _id was UUID
        curated_key = None
        for k, v in DISTRICT_4_CURATED_POIS.items():
            if v["vi"]["name"].lower() == vi_data["name"].lower():
                curated_key = k
                break

        # 2. Update localizations collection (upsert each language)
        for lang, item in translations_doc.items():
            loc_doc = {
                "_id": f"{poi_id}_{lang}",
                "poi_id": poi_id,
                "lang": lang,
                "name": item["name"],
                "description": item["description"],
                "audio_url": item["audio_url"],
                "audio_storage_key": item.get("audio_storage_key"),
                "audio_duration_ms": item["audio_duration_ms"],
                "audio_status": "ready",
                "audio_source": "google_tts",
                "translation_status": "ready",
                "updated_at": now,
                "version": 1
            }
            try:
                await poi_repo.localizations_collection.update_one(
                    {"poi_id": poi_id, "lang": lang},
                    {"$set": loc_doc},
                    upsert=True
                )

                # If this POI has a known slug ID (e.g. poi_ben_nha_rong), update that slug too
                if curated_key and curated_key != poi_id:
                    loc_slug_doc = dict(loc_doc)
                    loc_slug_doc["_id"] = f"{curated_key}_{lang}"
                    loc_slug_doc["poi_id"] = curated_key
                    await poi_repo.localizations_collection.update_one(
                        {"poi_id": curated_key, "lang": lang},
                        {"$set": loc_slug_doc},
                        upsert=True
                    )
            except Exception as e:
                logger.warning(f"Could not update localizations_collection for {poi_id}_{lang}: {e}")

        return translations_doc


translation_service = TranslationService()
