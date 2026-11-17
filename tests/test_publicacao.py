import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_gitignore_protege_artefatos_locais(tmp_path):
    shutil.copyfile(ROOT / ".gitignore", tmp_path / ".gitignore")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, capture_output=True)
    privados = [
        ".env",
        ".env.production",
        "db.sqlite3",
        ".demo/local.postman_environment.json",
        "local.postman_environment.json",
        ".venv/Scripts/python.exe",
        ".tools-node/node_modules/newman/package.json",
        ".npm-cache/log",
        ".agents/skills/exemplo/SKILL.md",
    ]
    publicos = [
        ".env.example",
        "README.md",
        "pyproject.toml",
        "uv.lock",
        "collections/postman/helpdesk.postman_collection.json",
        "collections/postman/local.example.postman_environment.json",
    ]
    resultado = subprocess.run(
        ["git", "-C", str(tmp_path), "check-ignore", "--no-index", "--stdin", "-z"],
        input=b"\0".join(x.encode() for x in privados + publicos) + b"\0",
        capture_output=True,
        check=False,
    )
    assert resultado.returncode == 0
    assert {x.decode() for x in resultado.stdout.split(b"\0") if x} == set(privados)


def test_colecao_publica_sem_credenciais():
    colecao = json.loads(
        (ROOT / "collections/postman/helpdesk.postman_collection.json").read_text(encoding="utf-8")
    )
    assert len(colecao["item"]) == 29
    assert colecao["info"]["schema"].endswith("/v2.1.0/collection.json")
    for item in colecao["item"]:
        request = item["request"]
        if request["url"].endswith("/auth/login/"):
            campos = {x["key"]: x["value"] for x in request["body"]["urlencoded"]}
            assert campos["password"].startswith("{{") and campos["password"].endswith("}}")
    ambiente = json.loads(
        (ROOT / "collections/postman/local.example.postman_environment.json").read_text(
            encoding="utf-8"
        )
    )
    for value in ambiente["values"]:
        if "password" in value["key"] or value["key"].startswith(("access_", "refresh_")):
            assert value["value"] == ""
