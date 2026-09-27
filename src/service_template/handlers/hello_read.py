import os
from urllib.parse import unquote

import boto3
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext

from service_template.dynamo import strip_internal_keys
from service_template.errors import DomainError, NotFoundError
from service_template.http import api_error_response, api_response
from service_template.observability import logger, metrics, tracer

app = APIGatewayHttpResolver()


@app.exception_handler(DomainError)
def handle_domain_error(exc):
    return api_error_response(exc)


@app.not_found
def handle_not_found(exc):
    return api_response(404, {"error": "rota não encontrada"})


def _table():
    return boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])


# TODO: exemplo de rota pública de leitura. Troque "/hello" pelo prefixo de
# rota do serviço (ADR-03) e "HELLO#" pelo namespace de PK da entidade real —
# em terraform-aws/api.tf e no registro de rotas da plataforma.
@app.get("/hello/<id>")
def get_hello(id: str):
    id = unquote(id)
    item = _table().get_item(Key={"PK": f"HELLO#{id}", "SK": "META"}).get("Item")
    if item is None:
        raise NotFoundError("item não encontrado")
    return api_response(200, strip_internal_keys(item))


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_HTTP)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: dict, context: LambdaContext):
    return app.resolve(event, context)
