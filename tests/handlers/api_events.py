def http_event(
    method: str,
    path: str,
    *,
    query: dict | None = None,
    body: str | None = None,
    groups: str | None = None,
    uid: str | None = None,
    headers: dict | None = None,
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
        "headers": headers or {},
        "isBase64Encoded": False,
        "queryStringParameters": query,
        "body": body,
    }
    if groups is not None or uid is not None:
        claims = {}
        if uid is not None:
            claims["custom:uid"] = uid
        if groups is not None:
            claims["cognito:groups"] = groups
        event["requestContext"]["authorizer"] = {"jwt": {"claims": claims}}
    return event
