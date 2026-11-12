import functools
import json
import logging
import os
import uuid

import azure.functions as func
from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableServiceClient, UpdateMode
from azure.identity import DefaultAzureCredential

app = func.FunctionApp()

TABLE_NAME = os.environ.get("TABLE_NAME", "accessreviews")
PARTITION_KEY = "accessreviews"
_table_client = None

def table():
    global _table_client
    if _table_client is None:
        service = TableServiceClient(
            endpoint=os.environ.get("STORAGE_TABLE_ENDPOINT"),
            credential=DefaultAzureCredential(),
        )
        _table_client = service.create_table_if_not_exists(TABLE_NAME)
    return _table_client


def to_record(entity):
    record = {k: v for k, v in entity.items() if k not in ("PartitionKey", "RowKey")}
    record["id"] = entity["RowKey"]
    return record

def all_access_reviews():
    entities = table().query_entities(f"PartitionKey eq '{PARTITION_KEY}'")
    return [to_record(e) for e in entities]

def check_flat(body):
    for key, value in body.items():
        if isinstance(value, (dict, list)):
            raise ValueError(f"'{key}' must be a string, number, or boolean, not a nested object or array")
        


class AuthError(Exception):
    pass
class NotFoundError(Exception):
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



def validateAdminToken(request: func.HttpRequest):
    admin_key = os.environ.get("adminkey")
    if not admin_key:
        raise RuntimeError("Admin key not configured on the server")
    if request.headers.get("x-admin-key") != admin_key:
        raise AuthError("Unauthorized: Admin key required for purge")



    
def find_access_review(request: func.HttpRequest):
    group_id = request.route_params.get("id")
    try:
        table().get_entity(partition_key=PARTITION_KEY, row_key=group_id)
    except ResourceNotFoundError:
        raise NotFoundError(f"Access review with ID {group_id} not found")
    return group_id


@app.route(route="access-reviews", methods=["GET"], auth_level = func.AuthLevel.ANONYMOUS)
@handle_exceptions
def get_access_reviews(req: func.HttpRequest) -> func.HttpResponse:
    validateToken(req)
    return func.HttpResponse(
        json.dumps(all_access_reviews()),
        status_code=200,
        mimetype="application/json",
    )


@app.route(route="access-reviews", methods=["POST"], auth_level = func.AuthLevel.ANONYMOUS)
@handle_exceptions
def create_access_review(req: func.HttpRequest) -> func.HttpResponse:
    validateToken(req)
    body = req.get_json()
    if not isinstance(body, dict):
        raise ValueError("Request body must be a JSON object")
    check_flat(body)
    group_id = str(uuid.uuid4())
    body["id"] = group_id
    table().create_entity({"PartitionKey": PARTITION_KEY, "RowKey": group_id, **body})
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
    if not isinstance(body, dict):
        raise ValueError("Request body must be a JSON object")
    check_flat(body)
    body["id"] = group_id
    table().upsert_entity(
        {"PartitionKey": PARTITION_KEY, "RowKey": group_id, **body},
        mode=UpdateMode.REPLACE,
    )
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
    table().delete_entity(partition_key=PARTITION_KEY, row_key=group_id)
    return func.HttpResponse(
        json.dumps({"message": f"Access review with ID {group_id} deleted"}),
        status_code=200,
        mimetype="application/json"
    )

##########################################EXTRA#####################################################

@app.route(route="access-reviews", methods=["DELETE"], auth_level = func.AuthLevel.ANONYMOUS)
@handle_exceptions
def purge_access_review(req: func.HttpRequest) -> func.HttpResponse:
    validateToken(req)
    validateAdminToken(req)
    reviews = all_access_reviews()
    for review in reviews:
        table().delete_entity(partition_key=PARTITION_KEY, row_key=review["id"])
    deleted = len(reviews)
    return func.HttpResponse(
        json.dumps({"message": f"All access reviews deleted. Total deleted: {deleted}"}),
        status_code=200,
        mimetype="application/json"
    )

@app.route(route="access-reviews/count", methods=["GET"], auth_level = func.AuthLevel.ANONYMOUS)
@handle_exceptions
def count_access_review(req: func.HttpRequest) -> func.HttpResponse:
    validateToken(req)
    return func.HttpResponse(
        json.dumps({"count": len(all_access_reviews())}),
        status_code=200,
        mimetype="application/json"
    )


@app.route(route="access-reviews/{id}", methods=["GET"], auth_level = func.AuthLevel.ANONYMOUS)
@handle_exceptions
def get_access_review(req: func.HttpRequest) -> func.HttpResponse:
    validateToken(req)
    group_id = find_access_review(req)
    entity = table().get_entity(partition_key=PARTITION_KEY, row_key=group_id)
    return func.HttpResponse(
        json.dumps(to_record(entity)),
        status_code=200,
        mimetype="application/json"
    )