data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

locals {
  read_actions  = jsonencode(["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"])
  write_actions = jsonencode(["dynamodb:GetItem", "dynamodb:Query", "dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:ConditionCheckItem"])

  # TODO: troque pelas funções reais do serviço (chave curta => módulo Python
  # em service_template.handlers). O exemplo abaixo é o par hello-read/hello-write.
  lambda_functions = {
    hello-read  = { module = "hello_read", access = "read" }
    hello-write = { module = "hello_write", access = "write" }
  }

  function_names = { for key, _ in local.lambda_functions : key => "${local.product}-${local.service}-${key}" }
}

module "lambda_role" {
  for_each = local.lambda_functions
  # TODO: `shd-terraform-aws-modules` ainda não publica um módulo `iam-role`
  # (só tem apigw-http-api e github-oidc no momento em que este template foi
  # escrito). Enquanto isso, aponte para uma fonte própria com ref fixado num
  # commit, ou publique o módulo em shd-terraform-aws-modules e consuma por
  # tag (ADR-11) antes de usar este template em produção.
  source = "TODO://fonte-do-modulo-iam-role"

  product    = local.product
  repository = local.repository

  role_name                   = "${local.service}-${each.key}-role"
  assume_role_policy_document = file("${path.module}/iam_templates/roles/lambda_assume_role.tftpl")

  policies = concat(
    [
      {
        name        = "${local.service}-${each.key}-basic-execution"
        description = "Permissões padrão de execução (logs), comuns a toda função Lambda"
        document = templatefile("${path.module}/iam_templates/policies/lambda_basic_execution_policy.tftpl", {
          region        = data.aws_region.current.region
          account_id    = data.aws_caller_identity.current.account_id
          function_name = local.function_names[each.key]
        })
      },
      {
        name        = "${local.service}-${each.key}-dynamodb"
        description = "Acesso ${each.value.access} à tabela ${local.service}"
        document = templatefile("${path.module}/iam_templates/policies/lambda_dynamodb_policy.tftpl", {
          actions   = each.value.access == "read" ? local.read_actions : local.write_actions
          table_arn = aws_dynamodb_table.table.arn
        })
      }
    ],
    each.value.access == "write" ? [
      {
        name        = "${local.service}-${each.key}-events"
        description = "Publicação de eventos de domínio"
        document = templatefile("${path.module}/iam_templates/policies/lambda_events_policy.tftpl", {
          event_bus_arn = data.aws_ssm_parameter.event_bus_arn.insecure_value
        })
      }
    ] : []
  )

  tags = local.tags
}
