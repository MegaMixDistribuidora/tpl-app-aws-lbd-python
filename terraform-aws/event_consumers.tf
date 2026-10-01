# Consumo de eventos de outros serviços: regra no bus → fila SQS (com DLQ) →
# Lambda. O consumidor deve ser idempotente por `id` do evento e devolver
# `batchItemFailures` (ReportBatchItemFailures).

locals {
  # TODO: consumidores deste serviço. Chave = nome curto (vira parte do nome da
  # fila); `function` aponta para local.lambda_functions; `pattern_extra`
  # (opcional) acrescenta campos ao padrão do evento. Exemplo:
  #   order-created = {
  #     function      = "stock-manager"
  #     sources       = ["megamix.orders"]
  #     detail_types  = ["OrderCreated"]
  #     pattern_extra = { detail = { status = ["created"] } }
  #   }
  event_consumers = {}

  consumer_queue_arns = {
    for fn in distinct([for _, c in local.event_consumers : c.function]) : fn => [
      for name, c in local.event_consumers : aws_sqs_queue.event_consumer[name].arn if c.function == fn
    ]
  }
}

# Falha cedo, com mensagem clara, se um mapa aponta para função inexistente.
resource "terraform_data" "function_keys_check" {
  lifecycle {
    precondition {
      condition     = alltrue([for _, c in local.event_consumers : contains(keys(local.lambda_functions), c.function)])
      error_message = "event_consumers: `function` precisa ser uma chave de local.lambda_functions."
    }
    precondition {
      condition     = alltrue([for _, fn in local.internal_routes : contains(keys(local.lambda_functions), fn)])
      error_message = "internal_routes: o valor precisa ser uma chave de local.lambda_functions."
    }
    precondition {
      condition     = alltrue([for fn, _ in local.internal_api_calls : contains(keys(local.lambda_functions), fn)])
      error_message = "internal_api_calls: a chave precisa ser uma chave de local.lambda_functions."
    }
  }
}

resource "aws_sqs_queue" "event_consumer_dlq" {
  for_each = local.event_consumers

  name                      = "${local.product}-${local.service}-${each.key}-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true

  tags = local.tags
}

resource "aws_sqs_queue" "event_consumer" {
  for_each = local.event_consumers

  name                    = "${local.product}-${local.service}-${each.key}"
  sqs_managed_sse_enabled = true
  # Precisa ser >= timeout da função consumidora; 6x é a recomendação da AWS.
  # Usa local.lambda_timeout (não o recurso) para não criar ciclo com a role.
  visibility_timeout_seconds = max(60, local.lambda_timeout * 6)

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.event_consumer_dlq[each.key].arn
    maxReceiveCount     = 3
  })

  depends_on = [terraform_data.function_keys_check]

  tags = local.tags
}

resource "aws_cloudwatch_event_rule" "event_consumer" {
  for_each = local.event_consumers

  name           = "${local.product}-${local.service}-${each.key}"
  event_bus_name = data.aws_ssm_parameter.event_bus_name.insecure_value

  event_pattern = jsonencode(merge(
    {
      source        = each.value.sources
      "detail-type" = each.value.detail_types
    },
    try(each.value.pattern_extra, {})
  ))

  tags = local.tags
}

resource "aws_cloudwatch_event_target" "event_consumer" {
  for_each = local.event_consumers

  rule           = aws_cloudwatch_event_rule.event_consumer[each.key].name
  event_bus_name = data.aws_ssm_parameter.event_bus_name.insecure_value
  arn            = aws_sqs_queue.event_consumer[each.key].arn
}

resource "aws_sqs_queue_policy" "event_consumer" {
  for_each = local.event_consumers

  queue_url = aws_sqs_queue.event_consumer[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowEventBridgeSend"
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sqs:SendMessage"
      Resource  = aws_sqs_queue.event_consumer[each.key].arn
      Condition = { ArnEquals = { "aws:SourceArn" = aws_cloudwatch_event_rule.event_consumer[each.key].arn } }
    }]
  })
}

resource "aws_lambda_event_source_mapping" "event_consumer" {
  for_each = local.event_consumers

  event_source_arn        = aws_sqs_queue.event_consumer[each.key].arn
  function_name           = aws_lambda_function.function[each.value.function].arn
  batch_size              = 10
  function_response_types = ["ReportBatchItemFailures"]

  depends_on = [module.lambda_role]
}

resource "aws_cloudwatch_metric_alarm" "event_consumer_dlq" {
  for_each = local.event_consumers

  alarm_name          = "${local.product}-${local.service}-${each.key}-dlq-not-empty"
  alarm_description   = "Mensagens na DLQ do consumidor ${each.key}"
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  dimensions          = { QueueName = aws_sqs_queue.event_consumer_dlq[each.key].name }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  tags = local.tags
}
