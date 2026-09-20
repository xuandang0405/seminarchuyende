import os
import sys
import asyncio

sys.stdout.reconfigure(encoding='utf-8')
from app.core.database import connect_to_mongo, get_database

async def check_all():
    await connect_to_mongo()
    db = get_database()
    pois = await db['pois'].find({'deleted_at': None}).to_list(100)
    print(f'Total active POIs in DB: {len(pois)}')
    for p in pois:
        p_id = str(p.get('_id'))
        p_name = p.get('name', '')[:25]
        trans = p.get('translations') or {}
        missing = []
        for l in ['vi', 'en', 'fr', 'ja', 'ko', 'zh']:
            url = trans.get(l, {}).get('audio_url') if isinstance(trans.get(l), dict) else None
            filename = f'{p_id}_{l}.mp3'
            path1 = os.path.join('backend/storage/audio', filename)
            path2 = os.path.join('backend/storage/audio', f'poi_{p_id}_{l}.mp3')
            path3 = os.path.join('backend/storage/audio', os.path.basename(url)) if url else ''
            exists = os.path.exists(path1) or os.path.exists(path2) or (path3 and os.path.exists(path3))
            if not exists:
                missing.append(l)
        if missing:
            print(f'POI {p_id} ({p_name}): MISSING AUDIO for {missing}')
        else:
            print(f'POI {p_id} ({p_name}): All 6 audio files exist')

if __name__ == '__main__':
    asyncio.run(check_all())
