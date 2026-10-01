data "aws_ssm_parameter" "api_id" {
  name = "/megamix/apigw/admin/api/id"
}

data "aws_ssm_parameter" "api_execution_arn" {
  name = "/megamix/apigw/admin/api/execution-arn"
}

data "aws_ssm_parameter" "staff_authorizer_id" {
  name = "/megamix/apigw/admin/authorizers/staff/id"
}

data "aws_ssm_parameter" "audit_table_name" {
  name = "/megamix/audit/table/name"
}

data "aws_ssm_parameter" "audit_table_arn" {
  name = "/megamix/audit/table/arn"
}

data "aws_ssm_parameter" "event_bus_name" {
  name = "/megamix/eventbridge/megamix-events/name"
}

data "aws_ssm_parameter" "event_bus_arn" {
  name = "/megamix/eventbridge/megamix-events/arn"
}

# API interna (AWS_IAM): chamadas serviço a serviço (ADR-31).
data "aws_ssm_parameter" "internal_api_id" {
  name = "/megamix/apigw/internal/api/id"
}

data "aws_ssm_parameter" "internal_api_execution_arn" {
  name = "/megamix/apigw/internal/api/execution-arn"
}

data "aws_ssm_parameter" "internal_api_endpoint" {
  name = "/megamix/apigw/internal/api/endpoint"
}

# Ids das APIs da loja e do portal: audience.py usa para saber de qual API veio
# a requisição.
data "aws_ssm_parameter" "store_api_id" {
  name = "/megamix/apigw/store/api/id"
}
