from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.views import exception_handler


class Conflito(APIException):
    status_code = 409
    default_detail = "Operação incompatível com o estado atual."
    default_code = "conflito"


def api_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        exc = ValidationError(getattr(exc, "message_dict", exc.messages))
    if isinstance(exc, IntegrityError):
        exc = ValidationError({"detail": "Dados duplicados ou inconsistentes."})
    response = exception_handler(exc, context)
    if response is None:
        return None
    codes = {
        400: "dados_invalidos",
        401: "nao_autenticado",
        403: "permissao_negada",
        404: "nao_encontrado",
        405: "metodo_nao_permitido",
        409: "conflito",
        429: "limite_excedido",
    }
    details = response.data
    message = details.get("detail") if isinstance(details, dict) else None
    response.data = {
        "error": {
            "code": codes.get(response.status_code, "erro_api"),
            "message": str(message) if message else "Verifique os dados enviados.",
            "details": details,
        }
    }
    return response
