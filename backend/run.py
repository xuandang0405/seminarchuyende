import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import uvicorn

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import settings

if __name__ == "__main__":
    reload_env = os.environ.get("UVICORN_RELOAD")
    if reload_env is not None:
        reload_flag = reload_env.lower() in ("1", "true", "yes")
    else:
        reload_flag = getattr(settings, "APP_ENV", "development") != "production"

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

    app_dir = os.path.join(backend_dir, "app")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=reload_flag,
        reload_dirs=[app_dir] if reload_flag else None,
        reload_excludes=["*storage*", "*uploads*", "*.mp3", "*.log"] if reload_flag else None,
    )

