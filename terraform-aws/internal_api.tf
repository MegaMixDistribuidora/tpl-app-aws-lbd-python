# API interna (AWS_IAM, ADR-31): rotas que este serviço expõe a outros serviços
# e chamadas que ele faz às rotas de outros serviços.

locals {
  internal_api_id            = data.aws_ssm_parameter.internal_api_id.insecure_value
  internal_api_execution_arn = data.aws_ssm_parameter.internal_api_execution_arn.insecure_value

  # TODO: rotas internas que este serviço expõe; a chave do mapa aponta para
  # local.lambda_functions. Exemplo:
  #   "GET /catalog/products/{id}" = "product-manager"
  internal_routes = {}

  # TODO: rotas internas de outros serviços que este serviço chama (concede
  # execute-api:Invoke à função). Chave = função, valor = "MÉTODO /caminho".
  # Exemplo:
  #   product-manager = ["GET /catalog/products/{id}"]
  internal_api_calls = {}

  # {param} vira * no ARN de execute-api.
  internal_api_resources = {
    for fn, calls in local.internal_api_calls : fn => [
      for call in calls :
      "${local.internal_api_execution_arn}/$default/${split(" ", call)[0]}${replace(split(" ", call)[1], "/\\{[^}]+\\}/", "*")}"
    ]
  }
}

resource "aws_apigatewayv2_integration" "internal" {
  for_each = toset(distinct(values(local.internal_routes)))

  api_id                 = local.internal_api_id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.function[each.key].invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "internal" {
  for_each = local.internal_routes

  api_id             = local.internal_api_id
  route_key          = each.key
  target             = "integrations/${aws_apigatewayv2_integration.internal[each.value].id}"
  authorization_type = "AWS_IAM"
}

resource "aws_lambda_permission" "internal_api" {
  for_each = toset(distinct(values(local.internal_routes)))

  statement_id  = "AllowInternalApiInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.function[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${local.internal_api_execution_arn}/*/*"
}
