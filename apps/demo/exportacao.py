import json
import os
import tempfile
from pathlib import Path


def gravar_atomico(path, conteudo, substituir=False):
    path = Path(path)
    if path.is_symlink() or path.parent.is_symlink():
        raise OSError("Ambiente não pode usar caminho simbólico.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporario = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".seed-", delete=False) as arquivo:
            temporario = Path(arquivo.name)
            os.chmod(temporario, 0o600)
            arquivo.write(conteudo)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        if substituir:
            os.replace(temporario, path)
        else:
            # Link exclusivo publica arquivo completo sem sobrescrever destino concorrente.
            os.link(temporario, path)
    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)


def exportar_ambiente(path, *, manifesto, contas, senhas, substituir=False):
    valores = {"base_url": "http://127.0.0.1:8000", "demo_uid": str(manifesto.uid)}
    for papel, usuario in contas.items():
        valores[f"{papel}_email"] = usuario.email
        valores[f"{papel}_password"] = senhas[papel]
        valores[f"access_{papel}"] = ""
        valores[f"refresh_{papel}"] = ""
    valores["categoria_id"] = str(manifesto.dados["categorias"]["acesso"])
    valores.update(
        {f"demo_{key}_id": str(value) for key, value in manifesto.dados["chamados"].items()}
    )
    payload = {
        "id": str(manifesto.uid),
        "name": "Help Desk - local privado",
        "values": [
            {
                "key": k,
                "value": v,
                "enabled": True,
                "type": "secret"
                if "password" in k or k.startswith(("access_", "refresh_"))
                else "default",
            }
            for k, v in valores.items()
        ],
        "_postman_variable_scope": "environment",
    }
    gravar_atomico(
        path, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"), substituir
    )
