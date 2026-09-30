# Outbox (ADR-27): os handlers gravam o item EVENT# na mesma transação da
# alteração; esta função lê o Stream da tabela e publica no bus. É a única
# função com events:PutEvents e a única consumidora do Stream.

locals {
  publisher_name = "${local.product}-${local.service}-event-publisher"
}

resource "aws_sqs_queue" "event_publisher_dlq" {
  name                      = "${local.publisher_name}-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true

  tags = local.tags
}

module "event_publisher_role" {
  # TODO: mesma fonte do módulo `iam-role` de iam.tf.
  source = "TODO://fonte-do-modulo-iam-role"

  product    = local.product
  repository = local.repository

  role_name                   = "${local.service}-event-publisher-role"
  assume_role_policy_document = file("${path.module}/iam_templates/roles/lambda_assume_role.tftpl")

  policies = [
    {
      name        = "${local.service}-event-publisher-basic-execution"
      description = "Permissões padrão de execução (logs), comuns a toda função Lambda"
      document = templatefile("${path.module}/iam_templates/policies/lambda_basic_execution_policy.tftpl", {
        region        = data.aws_region.current.region
        account_id    = data.aws_caller_identity.current.account_id
        function_name = local.publisher_name
      })
    },
    {
      name        = "${local.service}-event-publisher-outbox"
      description = "Leitura do Stream da tabela ${local.service}, publicação no bus e DLQ"
      document = templatefile("${path.module}/iam_templates/policies/lambda_event_publisher_policy.tftpl", {
        stream_arn    = aws_dynamodb_table.table.stream_arn
        event_bus_arn = data.aws_ssm_parameter.event_bus_arn.insecure_value
        dlq_arn       = aws_sqs_queue.event_publisher_dlq.arn
      })
    }
  ]

  tags = local.tags
}

resource "aws_lambda_function" "event_publisher" {
  function_name = local.publisher_name
  role          = module.event_publisher_role.role_arn
  # TODO: troque "service_template" pelo nome real do pacote Python.
  handler       = "service_template.handlers.event_publisher.handler"
  runtime       = "python3.12"
  architectures = [local.lambda_architecture]
  layers        = [local.powertools_layer_arn]
  timeout       = 30
  memory_size   = 128

  filename         = data.archive_file.service.output_path
  source_code_hash = data.archive_file.service.output_base64sha256

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = {
      EVENT_BUS_NAME               = data.aws_ssm_parameter.event_bus_name.insecure_value
      POWERTOOLS_SERVICE_NAME      = local.service
      POWERTOOLS_METRICS_NAMESPACE = "MegaMix"
      LOG_LEVEL                    = "INFO"
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda]

  tags = local.tags
}

resource "aws_lambda_event_source_mapping" "outbox_stream" {
  event_source_arn  = aws_dynamodb_table.table.stream_arn
  function_name     = aws_lambda_function.event_publisher.arn
  starting_position = "TRIM_HORIZON"
  batch_size        = 10

  # Só itens de evento novos; entidade, auditoria e remoção pelo TTL ficam de fora.
  filter_criteria {
    filter {
      pattern = jsonencode({
        eventName = ["INSERT"]
        dynamodb  = { Keys = { PK = { S = [{ prefix = "EVENT#" }] } } }
      })
    }
  }

  # Registro com falha é retentado a partir dele (consumidores são idempotentes
  # por `id`); esgotadas as tentativas, a referência vai para a DLQ.
  function_response_types = ["ReportBatchItemFailures"]
  maximum_retry_attempts  = 10

  destination_config {
    on_failure {
      destination_arn = aws_sqs_queue.event_publisher_dlq.arn
    }
  }

  depends_on = [module.event_publisher_role]
}
