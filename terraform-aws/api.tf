locals {
  api_id = data.aws_ssm_parameter.api_id.insecure_value

  # TODO: troque "/hello" pelo prefixo de rota real do serviço (ADR-03) e as
  # rotas pelas rotas reais; a chave do mapa aponta para local.lambda_functions.
  public_routes = {
    "GET /hello/{id}" = "hello-read"
  }

  staff_routes = {
    "POST /hello" = "hello-write"
  }
}

resource "aws_apigatewayv2_integration" "function" {
  for_each = local.lambda_functions

  api_id                 = local.api_id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.function[each.key].invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "public" {
  for_each = local.public_routes

  api_id             = local.api_id
  route_key          = each.key
  target             = "integrations/${aws_apigatewayv2_integration.function[each.value].id}"
  authorization_type = "NONE"
}

resource "aws_apigatewayv2_route" "staff" {
  for_each = local.staff_routes

  api_id             = local.api_id
  route_key          = each.key
  target             = "integrations/${aws_apigatewayv2_integration.function[each.value].id}"
  authorization_type = "JWT"
  authorizer_id      = data.aws_ssm_parameter.staff_authorizer_id.insecure_value
}

resource "aws_lambda_permission" "api" {
  for_each = local.lambda_functions

  statement_id  = "AllowSharedApiInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.function[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  # TODO: troque "hello" pelo prefixo de rota real do serviço.
  source_arn = "${data.aws_ssm_parameter.api_execution_arn.insecure_value}/*/*/hello/*"
}
