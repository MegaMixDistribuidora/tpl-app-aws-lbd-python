data "aws_ssm_parameter" "api_id" {
  name = "/megamix/apigw/admin/api/id"
}

data "aws_ssm_parameter" "api_execution_arn" {
  name = "/megamix/apigw/admin/api/execution-arn"
}

data "aws_ssm_parameter" "staff_authorizer_id" {
  name = "/megamix/apigw/admin/authorizers/staff/id"
}

data "aws_ssm_parameter" "event_bus_name" {
  name = "/megamix/eventbridge/megamix-events/name"
}

data "aws_ssm_parameter" "event_bus_arn" {
  name = "/megamix/eventbridge/megamix-events/arn"
}
