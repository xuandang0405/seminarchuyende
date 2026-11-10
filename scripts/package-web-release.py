"""Build the uploadable TourVoice release from an allowlist of runtime files."""
import argparse
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    ".dockerignore", "backend/Dockerfile", "backend/requirements.lock", "backend/worker.py",
    "apps/web-admin/package.json", "apps/web-admin/package-lock.json", "apps/web-admin/index.html",
    "apps/web-admin/postcss.config.js", "apps/web-admin/tailwind.config.js",
    "apps/web-admin/tsconfig.json", "apps/web-admin/vite.config.ts",
    "deploy/docker-compose.prod.yml", "deploy/env/.env.production.example",
    "deploy/nginx/docker.conf", "deploy/scripts/deploy.sh", "deploy/scripts/smoke-test.sh",
    "deploy/README_DEPLOY.md", "docs/WEB_APP_SCOPE.md",
)
DIRECTORIES = ("backend/app", "apps/web-admin/src", "apps/web-admin/public", "shared", "deploy/demo")


def deployment_files():
    for name in FILES:
        yield ROOT / name
    for name in DIRECTORIES:
        folder = ROOT / name
        for path in sorted(folder.rglob("*")):
            parts = path.relative_to(folder).parts
            if path.is_symlink() or not path.is_file():
                continue
            if any(part.startswith(".") or part in {"__pycache__", "node_modules", "tests"} for part in parts):
                continue
            yield path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, nargs="?", default=ROOT / "release/tourvoice-web-deploy.tar.gz")
    output = parser.parse_args().output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as archive:
        for path in deployment_files():
            archive.add(path, arcname="tourvoice-web/" + path.relative_to(ROOT).as_posix(), recursive=False)
    print(f"{output} ({output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
