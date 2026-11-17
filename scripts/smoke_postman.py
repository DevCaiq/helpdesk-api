"""Executa Newman contra servidor efêmero e SQLite isolado, sem usar db.sqlite3."""

import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    newman = ROOT / ".tools-node" / "node_modules" / "newman" / "bin" / "newman.js"
    if not newman.is_file():
        raise SystemExit(
            "Instale Newman conforme docs/demo.md; ferramenta opcional de verificação."
        )
    cache = ROOT / ".pytest_cache"
    cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="postman-", dir=cache) as tmp:
        tmp = Path(tmp)
        env = os.environ.copy()
        env.pop("DEMO_PASSWORD", None)
        env.update(
            {
                "DJANGO_SETTINGS_MODULE": "config.settings.dev",
                "SQLITE_PATH": str(tmp / "smoke.sqlite3"),
                "SECRET_KEY": secrets.token_hex(32),
                "DEBUG": "False",
                "ALLOWED_HOSTS": "127.0.0.1,localhost",
            }
        )
        ambiente = tmp / "local.postman_environment.json"
        python = [sys.executable, str(ROOT / "manage.py")]
        subprocess.run(
            [*python, "migrate", "--noinput"], cwd=ROOT, env=env, check=True, capture_output=True
        )
        subprocess.run(
            [*python, "seed_demo", "--ambiente", str(ambiente)],
            cwd=ROOT,
            env=env,
            check=True,
            capture_output=True,
        )
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        dados = json.loads(ambiente.read_text(encoding="utf-8"))
        for item in dados["values"]:
            if item["key"] == "base_url":
                item["value"] = url
        ambiente.write_text(json.dumps(dados), encoding="utf-8")
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        with (tmp / "server.log").open("w", encoding="utf-8") as log:
            server = subprocess.Popen(
                [*python, "runserver", f"127.0.0.1:{port}", "--noreload", "--nothreading"],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=flags,
            )
            try:
                limite = time.monotonic() + 20
                while True:
                    if server.poll() is not None:
                        raise RuntimeError("Servidor de smoke encerrou antes de ficar pronto.")
                    try:
                        with urllib.request.urlopen(url + "/health/", timeout=1) as response:  # nosec B310
                            if response.status == 200:
                                break
                    except (urllib.error.URLError, TimeoutError):
                        if time.monotonic() >= limite:
                            raise RuntimeError("Servidor de smoke não ficou pronto.") from None
                        time.sleep(0.2)
                subprocess.run(
                    [
                        "node",
                        str(newman),
                        "run",
                        str(ROOT / "collections/postman/helpdesk.postman_collection.json"),
                        "--environment",
                        str(ambiente),
                        "--bail",
                        "--reporters",
                        "cli",
                        "--reporter-cli-no-console",
                        "--timeout-request",
                        "10000",
                    ],
                    cwd=ROOT,
                    env=env,
                    check=True,
                )
            finally:
                if os.name == "nt" and server.poll() is None:
                    # O launcher do venv no Windows pode ter um filho python.exe.
                    subprocess.run(
                        ["taskkill", "/PID", str(server.pid), "/T", "/F"],
                        capture_output=True,
                        check=True,
                    )
                elif server.poll() is None:
                    server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)


if __name__ == "__main__":
    main()
