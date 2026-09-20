"""Root launcher script for TourVoice Backend Server.

Allows running `python run.py` directly from project root.
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Locate backend directory
current_dir = os.path.dirname(os.path.abspath(__file__))
candidates = [
    os.path.join(current_dir, "backend"),
    os.path.join(current_dir, "seminarchuyende", "backend"),
]

backend_dir = None
for candidate in candidates:
    if os.path.exists(os.path.join(candidate, "app", "main.py")):
        backend_dir = candidate
        break

if not backend_dir:
    print("❌ LỖI: Không tìm thấy thư mục backend của TourVoice!")
    sys.exit(1)

os.chdir(backend_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    reload_env = os.environ.get("UVICORN_RELOAD")
    if reload_env is not None:
        reload_flag = reload_env.lower() in ("1", "true", "yes")
    else:
        reload_flag = settings.APP_ENV != "production"

    import socket
    def get_server_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    server_ip = get_server_ip()

    print("=" * 72)
    print(f"🚀 TOURVOICE FASTAPI SERVER ({settings.PROJECT_NAME})")
    print(f"🖥️  CHẾ ĐỘ MÁY CHỦ     : MÁY CHỦ TRỰC TIẾP (100% LIVE SERVER HOST)")
    print(f"🌐 Truy cập tại máy    : http://localhost:{settings.PORT}/admin/ | Docs: /docs")
    print(f"📡 Truy cập mạng LAN   : http://{server_ip}:{settings.PORT}/admin/ | Docs: /docs")
    if settings.PUBLIC_WEB_URL:
        print(f"🌍 Truy cập từ xa/WAN  : {settings.PUBLIC_WEB_URL}/admin/ | Docs: /docs")
    print(f"📱 Ứng Dụng Mobile      : React Native Expo (kết nối trực tiếp server này)")
    print(f"🔄 Tự động Reload       : {reload_flag}")
    print("=" * 72)

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=reload_flag,
        reload_dirs=[backend_dir] if reload_flag else None,
    )
