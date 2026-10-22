import functools
import json
import logging
import os
import uuid

import azure.functions as func

app = func.FunctionApp()

access-reviews = {}

class AuthError(Exception):
    pass

def handle_exceptions(handler):
    @functools.wraps(handler)
    def wrapper(*args, **kwargs):
        try:
            return handler(*args, **kwargs)
        except AuthError as exc:
            return func.HttpResponse(
                json.dumps({"error": str(exc)}),
                status_code=401,
                mimetype="application/json"
            )
        except Exception:
            logging.exception("Unhandled API exception")
            return func.HttpResponse(
                json.dumps({"error": "Internal Server Error"}),
                status_code=500,
                mimetype="application/json"
            )
    return wrapper



def getToken():
    api_key = os.environ.get("apikey")
    if not api_key:
        raise AuthError("API key not configured")
    return api_key


def validateToken(request: func.HttpRequest):
    token = getToken()
    if not token or request.headers.get("x-api-key") != token:
        raise AuthError("Unauthorized: Invalid or missing API key")
    
    