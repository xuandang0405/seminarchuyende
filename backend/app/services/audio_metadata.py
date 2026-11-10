from io import BytesIO
from mutagen.mp3 import MP3


def mp3_duration_ms(data):
    audio = MP3(BytesIO(data))
    if not audio.info or audio.info.length <= 0:
        raise ValueError("Tệp không phải audio MP3 hợp lệ.")
    return round(audio.info.length * 1000)
