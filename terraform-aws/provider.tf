provider "aws" {
  region = "sa-east-1"

  # Local: vem do AWS_PROFILE do ambiente. Na esteira fica null e o provider cai
  # na cadeia padrão de credenciais, que é a role assumida via OIDC.
  profile = var.aws_profile

  # Trava de segurança: se as credenciais resolvidas não pertencerem à conta
  # declarada no tfvars do ambiente, o Terraform aborta antes de planejar.
  # Sem isto, um profile errado aplica a configuração de um ambiente na conta
  # de outro.
  allowed_account_ids = [var.aws_account_id]
}

terraform {
  required_version = "1.14.9"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.40.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "2.7.1"
    }
  }

  # Bucket e key vêm do -backend-config passado pela esteira no init.
  backend "s3" {
    region = "sa-east-1"
  }
}
