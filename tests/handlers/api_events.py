def http_event(
    method: str,
    path: str,
    *,
    query: dict | None = None,
    body: str | None = None,
    groups: str | None = None,
    sub: str | None = None,
) -> dict:
    event = {
        "version": "2.0",
        "routeKey": f"{method} {path}",
        "rawPath": path,
        "rawQueryString": "",
        "requestContext": {
            "stage": "$default",
            "requestId": "test-request-id",
            "http": {"method": method, "path": path},
        },
        "headers": {},
        "isBase64Encoded": False,
        "queryStringParameters": query,
        "body": body,
    }
    if groups is not None or sub is not None:
        claims = {}
        if sub is not None:
            claims["sub"] = sub
        if groups is not None:
            claims["cognito:groups"] = groups
        event["requestContext"]["authorizer"] = {"jwt": {"claims": claims}}
    return event
