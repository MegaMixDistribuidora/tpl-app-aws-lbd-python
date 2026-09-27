# TODO: este é o desenho single-table com até 2 GSIs genéricos (byParent-like)
# usado pelo catalog-service (ADR-04). Ajuste os atributos e os GSIs aos
# padrões de acesso reais do novo serviço — pode ser que precise de menos (ou
# de nenhum) GSI, ou de nomes de índice mais descritivos que "byX"/"byY".
resource "aws_dynamodb_table" "table" {
  name         = "${local.product}-${local.service}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  global_secondary_index {
    # TODO: nomeie o índice pelo padrão de acesso real (ex.: "byParent").
    name            = "byX"
    hash_key        = "GSI1PK"
    range_key       = "GSI1SK"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  deletion_protection_enabled = true

  tags = local.tags
}
