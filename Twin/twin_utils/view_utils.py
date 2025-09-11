import json
from uuid import UUID
from django.http import HttpRequest, HttpResponse, JsonResponse


def is_ajax(request: HttpRequest) -> bool:
    """Examine if request is ajax.
    request.is_ajax() is deprecated since django 3.1
    """
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


# Custom JSON encoder to handle UUID objects
class UUIDEncoder(json.JSONEncoder):
    """Custom json encoder to handle objects containing UUID fields.
    Because uuid is not serializable, this custom function is needed.
    Example:
        data_dict = model_to_dict(data)
        ctx = {"data": data_dict}
        return HttpResponse(json.dumps(ctx, cls=UUIDEncoder), content_type="application/json")
    """

    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)
