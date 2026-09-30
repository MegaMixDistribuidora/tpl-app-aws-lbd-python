data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

locals {
  # TODO: deixe só as ações que os handlers reais usam (ADR-24).
  table_actions = jsonencode(["dynamodb:GetItem", "dynamodb:Query", "dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:ConditionCheckItem"])

  # TODO: troque pelas funções reais do serviço (chave curta => módulo Python
  # em service_template.handlers). Uma função por recurso, com leitura e escrita
  # juntas; o exemplo abaixo é o hello-manager.
  lambda_functions = {
    hello-manager = { module = "hello_manager" }
  }

  function_names = { for key, _ in local.lambda_functions : key => "${local.product}-${local.service}-${key}" }

  # TODO: troque "hello#*" pelos prefixos das entidades do serviço na tabela
  # `audit` (nome de entidade é único na plataforma, ADR-16).
  audit_leading_keys = jsonencode(["hello#*"])
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

  policies = [
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
      description = "Acesso à tabela ${local.service}"
      document = templatefile("${path.module}/iam_templates/policies/lambda_dynamodb_policy.tftpl", {
        actions   = local.table_actions
        table_arn = aws_dynamodb_table.table.arn
      })
    },
    {
      name        = "${local.service}-${each.key}-audit"
      description = "Gravação de auditoria das ações de staff"
      document = templatefile("${path.module}/iam_templates/policies/lambda_audit_policy.tftpl", {
        audit_table_arn = data.aws_ssm_parameter.audit_table_arn.insecure_value
        leading_keys    = local.audit_leading_keys
      })
    }
  ]

  tags = local.tags
}
