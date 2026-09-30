import os
from urllib.parse import unquote

import boto3
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext

from service_template import validation
from service_template.audit import audit_put, diff
from service_template.auth import actor_id, correlation_id, require_group
from service_template.dynamo import strip_internal_keys
from service_template.dynamo_format import item_to_dynamo
from service_template.errors import DomainError, NotFoundError
from service_template.outbox import event_put
from service_template.http import api_error_response, api_response, parse_body
from service_template.ids import new_id
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


_client = None


def _dynamodb_client():
    global _client
    if _client is None:
        _client = boto3.client("dynamodb")
    return _client


# TODO: uma função por recurso, com leitura e escrita juntas. É só um ponto de
# partida:
# - troque "hello"/"Hello"/"HELLO#" pelo nome real da entidade — em
#   terraform-aws/api.tf e iam.tf também;
# - na API do portal toda rota exige o grupo de staff, inclusive leitura
#   (ADR-03); troque os grupos pelas permissões reais do recurso (PRD §6.5);
# - substitua a validação por campos reais (adicione `*_fields` em validation.py);
# - se a entidade precisar de slug/SKU únicos, troque o put_item direto por um
#   repository.py com o padrão de itens-ponteiro em TransactWriteItems (ver
#   aws-megamix-app-lbd-catalog-service/docs/superpowers/specs);
# - troque "HelloCreated" pelo evento de domínio real (arquitetura.md §4), ou
#   tire o `event_put` se ninguém consome o fato (ADR-27);
# - troque a entidade "hello" da auditoria pelo nome real, o mesmo do
#   `dynamodb:LeadingKeys` em terraform-aws/iam.tf (ADR-16).
@app.get("/hello/<id>")
def get_hello(id: str):
    require_group(app.current_event.raw_event, allowed_groups=["Vendedor", "Administrador"])
    id = unquote(id)
    item = _table().get_item(Key={"PK": f"HELLO#{id}", "SK": "META"}).get("Item")
    if item is None:
        raise NotFoundError("item não encontrado")
    return api_response(200, strip_internal_keys(item))


@app.post("/hello")
def create_hello():
    raw_event = app.current_event.raw_event
    require_group(raw_event, allowed_groups=["Vendedor", "Administrador"])
    actor, correlation = actor_id(raw_event), correlation_id(raw_event)
    body = validation.require_object(parse_body(raw_event))
    name = validation.required_str(body, "name")
    id = new_id()
    item = {"PK": f"HELLO#{id}", "SK": "META", "id": id, "name": name}
    result = strip_internal_keys(item)
    table_name = os.environ["TABLE_NAME"]
    # Entidade, auditoria (ADR-16) e evento (ADR-27) na mesma transação: não há
    # alteração sem registro nem evento sem alteração.
    _dynamodb_client().transact_write_items(
        TransactItems=[
            {"Put": {"TableName": table_name, "Item": item_to_dynamo(item), "ConditionExpression": "attribute_not_exists(PK)"}},
            audit_put(
                os.environ["AUDIT_TABLE_NAME"],
                entity="hello",
                entity_id=id,
                action="created",
                actor_id=actor,
                correlation_id=correlation,
                changes=diff(None, result),
            ),
            event_put(table_name, "HelloCreated", {"helloId": id}, correlation_id=correlation),
        ]
    )
    return api_response(201, result)


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_HTTP)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: dict, context: LambdaContext):
    return app.resolve(event, context)
