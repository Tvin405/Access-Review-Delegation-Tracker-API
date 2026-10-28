import functools
import json
import logging
import os
import uuid

import azure.functions as func

app = func.FunctionApp()

access_reviews = {}

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
        except NotFoundError as exc:
            return func.HttpResponse(
                json.dumps({"error": str(exc)}),
                status_code=404,
                mimetype="application/json"
            )
        except ValueError as exc:
            return func.HttpResponse(
                json.dumps({"error": str(exc)}),
                status_code=400,
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
    
def find_access_review(request: func.HttpRequest):
    group_id = request.route_params.get("id")
    if group_id not in access_reviews:
        raise NotFoundError(f"Access review with ID {group_id} not found")
    return access_reviews[group_id]



@app.route(route="access-reviews", methods=["GET"], auth_level = func.AuthLevel.ANONYMOUS)
@handle_exceptions
def get_access_reviews(req: func.HttpRequest) -> func.HttpResponse:
    validateToken(req)
    return func.HttpResponse(
        json.dumps(list(access_reviews.values())),
        status_code=200,
        mimetype="application/json",
    )


@app.route(route="access-reviews", methods=["POST"], auth_level = func.AuthLevel.ANONYMOUS)
@handle_exceptions
def create_access_review(req: func.HttpRequest) -> func.HttpResponse:
    validateToken(req)

    body = req.get_json()
    group_id = str(uuid.uuid4())
    body["id"] = group_id
    access_reviews[group_id] = body
    return func.HttpResponse(
        json.dumps(body),
        status_code=201,
        mimetype="application/json"
    )

@app.route(route="access-reviews/{id}", methods=["PUT"], auth_level = func.AuthLevel.ANONYMOUS)
@handle_exceptions
def update_access_review(req: func.HttpRequest) -> func.HttpResponse:
    validateToken(req)
    group_id = find_access_review(req)
    body = req.get_json()
    body["id"] = group_id
    access_reviews[group_id] = body
    return func.HttpResponse(
        json.dumps(body),
        status_code=200,
        mimetype="application/json"
    )

@app.route(route="access-reviews/{id}", methods=["DELETE"], auth_level = func.AuthLevel.ANONYMOUS)
@handle_exceptions
def delete_access_review(req: func.HttpRequest) -> func.HttpResponse:
    validateToken(req)
    group_id = find_access_review(req)
    del access_reviews[group_id]
    return func.HttpResponse(
        json.dumps({"message": f"Access review with ID {group_id} deleted"}),
        status_code=200,
        mimetype="application/json"
    )

