variable "aws_profile" {
  description = "Perfil AWS local (null usa a cadeia de credenciais do OIDC na pipeline)."
  type        = string
  default     = null
}

variable "aws_account_id" {
  description = "Conta AWS esperada (latch de segurança)."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id deve ter 12 dígitos."
  }
}

variable "environment" {
  description = "dev ou prod."
  type        = string

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment deve ser dev ou prod."
  }
}
