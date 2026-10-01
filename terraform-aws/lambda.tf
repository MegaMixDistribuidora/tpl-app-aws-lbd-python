# TODO: troque "service_template" pelo nome real do pacote Python (o mesmo de
# src/<pacote>/) e "TODO-nome-do-servico" pelo nome do zip de saída.
data "archive_file" "service" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/../dist/TODO-nome-do-servico.zip"
  excludes    = ["**/__pycache__/**", "**/*.pyc"]
}

resource "aws_cloudwatch_log_group" "lambda" {
  for_each = merge(local.function_names, { event-publisher = local.publisher_name })

  name              = "/aws/lambda/${each.value}"
  retention_in_days = 30

  tags = local.tags
}

resource "aws_lambda_function" "function" {
  for_each = local.lambda_functions

  function_name = local.function_names[each.key]
  role          = module.lambda_role[each.key].role_arn
  # TODO: troque "service_template" pelo nome real do pacote Python.
  handler       = "service_template.handlers.${each.value.module}.handler"
  runtime       = "python3.12"
  architectures = [local.lambda_architecture]
  layers        = [local.powertools_layer_arn]
  timeout       = local.lambda_timeout
  memory_size   = 128

  filename         = data.archive_file.service.output_path
  source_code_hash = data.archive_file.service.output_base64sha256

  tracing_config {
    mode = "Active"
  }

  environment {
    variables = {
      TABLE_NAME                   = aws_dynamodb_table.table.name
      AUDIT_TABLE_NAME             = data.aws_ssm_parameter.audit_table_name.insecure_value
      POWERTOOLS_SERVICE_NAME      = local.service
      POWERTOOLS_METRICS_NAMESPACE = "MegaMix"
      LOG_LEVEL                    = "INFO"
      STORE_API_ID                 = data.aws_ssm_parameter.store_api_id.insecure_value
      ADMIN_API_ID                 = local.api_id
      INTERNAL_API_ID              = data.aws_ssm_parameter.internal_api_id.insecure_value
      INTERNAL_API_ENDPOINT        = data.aws_ssm_parameter.internal_api_endpoint.insecure_value
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda]

  tags = local.tags
}
