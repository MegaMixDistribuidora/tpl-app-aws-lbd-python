locals {
  organization = "MegaMixDistribuidora"
  product      = "megamix"
  # TODO: troque pelo nome real do repositório do novo serviço.
  repository = "github.com/${local.organization}/TODO-nome-do-repositorio"
  # TODO: nome curto do serviço (ex.: "catalog"). Usado no nome dos recursos
  # (tabela, funções Lambda, roles) e nas tags — mantenha consistente com
  # observability.py e handlers/event_publisher.py.
  service = "TODO-nome-do-servico"

  lambda_architecture = "arm64"

  # Layer gerenciada pela AWS: Logger, Tracer, Metrics e o Resolver do
  # Powertools. Runtime python3.12, arquitetura arm64. Versão travada
  # explicitamente; atualizar por PR quando a AWS publicar uma nova
  # (docs.aws.amazon.com/powertools/python/latest/getting-started/install/).
  # TODO: confirme se esta é a versão mais recente ao criar o serviço.
  powertools_layer_arn = "arn:aws:lambda:sa-east-1:017000801446:layer:AWSLambdaPowertoolsPythonV3-python312-arm64:38"

  tags = {
    Product     = local.product
    Service     = local.service
    Environment = var.environment
    ManagedBy   = "terraform"
    Repository  = local.repository
  }
}
