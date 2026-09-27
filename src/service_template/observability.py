from aws_lambda_powertools import Logger, Metrics, Tracer

# TODO: troque "service-template" pelo nome curto do serviço (o mesmo usado em
# terraform-aws/locals.tf como `local.service`).
logger = Logger(service="service-template")
tracer = Tracer(service="service-template")
metrics = Metrics(namespace="MegaMix", service="service-template")
