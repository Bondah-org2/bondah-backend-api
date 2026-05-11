def cleanup_openapi_schema(result, **kwargs):
    """
    Postprocess OpenAPI schema:
    - Remove empty enums
    - Remove empty descriptions
    """

    def clean(obj):
        if isinstance(obj, dict):
            # Remove empty enum values
            if "enum" in obj:
                obj["enum"] = [x for x in obj["enum"] if x not in ("", None)]

            # Remove empty descriptions
            if obj.get("description", None) == "":
                del obj["description"]

            for v in obj.values():
                clean(v)

        elif isinstance(obj, list):
            for item in obj:
                clean(item)

    clean(result)
    return result
