import json
import os

import boto3
from aws_lambda_powertools.utilities.batch import BatchProcessor, EventType, process_partial_response
from aws_lambda_powertools.utilities.data_classes.dynamo_db_stream_event import DynamoDBRecord
from aws_lambda_powertools.utilities.typing import LambdaContext

from service_template.dynamo import normalize_number
from service_template.observability import logger, metrics, tracer

# TODO: troque "service-template" pelo nome curto do serviço (arquitetura.md §4:
# `source = megamix.<serviço>`).
EVENT_SOURCE = "megamix.service-template"

# Um registro com falha não impede os demais; o Lambda retoma o shard a partir dele.
processor = BatchProcessor(event_type=EventType.DynamoDBStreams, raise_on_entire_batch_failure=False)

_client = None


def _events_client():
    global _client
    if _client is None:
        _client = boto3.client("events")
    return _client


def _is_outbox_insert(record: DynamoDBRecord) -> bool:
    # O filtro do event source mapping já só entrega INSERT de EVENT#; a checagem
    # repete a regra para que a remoção pelo TTL nunca republique um evento.
    if record.event_name is None or record.event_name.name != "INSERT":
        return False
    return str((record.dynamodb.keys or {}).get("PK", "")).startswith("EVENT#")


def publish(record: DynamoDBRecord) -> None:
    if not _is_outbox_insert(record):
        return
    item = normalize_number(record.dynamodb.new_image)
    detail = {
        "id": item["id"],
        "version": item["version"],
        "occurredAt": item["occurredAt"],
        "correlationId": item["correlationId"],
        "data": item["data"],
    }
    response = _events_client().put_events(
        Entries=[
            {
                "Source": EVENT_SOURCE,
                "DetailType": item["detailType"],
                "Detail": json.dumps(detail),
                "EventBusName": os.environ["EVENT_BUS_NAME"],
            }
        ]
    )
    if response.get("FailedEntryCount"):
        failure = response["Entries"][0]
        raise RuntimeError(f"evento {item['id']} recusado pelo bus: {failure.get('ErrorCode')}")
    logger.info("evento publicado", extra={"eventId": item["id"], "detailType": item["detailType"]})


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event: dict, context: LambdaContext):
    return process_partial_response(event=event, record_handler=publish, processor=processor, context=context)
