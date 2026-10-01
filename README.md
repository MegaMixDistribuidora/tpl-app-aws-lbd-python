# tpl-app-aws-lbd-python

Template de serviço Lambda Python serverless da Mega Mix (ADR-12), extraído do
`aws-megamix-app-lbd-catalog-service` depois que ele estabilizou. Use **"Use
this template"** no GitHub para criar um serviço novo — depois disso este
repositório não é mais consultado (sem dependência contínua, mesmo espírito do
ADR-11 para os `shd-*`).

Cobre só o scaffolding transversal: infraestrutura Terraform (ADR-04, ADR-09,
ADR-10), esteira CI/CD (`.github/workflows`, `.pipeline.yml`), testes e os
módulos Python de infraestrutura comuns a qualquer serviço de domínio (HTTP,
erros, autorização por grupo Cognito, observabilidade, eventos). Nenhuma
regra de negócio, nome de entidade ou dado da Mega Mix — é público
(`.claude/rules/seguranca.md` #3).

## Como usar

Todo ponto que precisa ser trocado ou completado está marcado com `TODO` no
próprio arquivo. Ordem sugerida:

1. **Nome do serviço** — `terraform-aws/locals.tf` (`service`, `repository`),
   `src/service_template/observability.py` e
   `src/service_template/handlers/event_publisher.py` (`EVENT_SOURCE`). Considere também renomear o pacote `service_template`
   para o nome real do serviço (ajuste os imports em todos os arquivos).
2. **Tabela e IAM** — `terraform-aws/dynamodb.tf` (GSIs conforme os padrões de
   acesso reais) e `terraform-aws/iam.tf` (funções Lambda reais, e a fonte do
   módulo `iam-role` — veja o `TODO` lá, `shd-terraform-aws-modules` ainda não
   publica esse módulo).
3. **Rotas** — `terraform-aws/api.tf` (prefixo de rota na API do portal,
   `megamix-admin-api`, ADR-03) e `terraform-aws/lambda.tf` (nome do zip).
4. **Handler de exemplo** — `src/service_template/handlers/hello_manager.py`
   (uma função por recurso, leitura e escrita juntas) mostra o padrão ponta a
   ponta (rota → autorização de grupo → validação → entidade, auditoria e
   evento de domínio numa só transação → resposta HTTP). O evento sai pelo
   outbox (ADR-27): a função `event-publisher` (`terraform-aws/event_publisher.tf`)
   lê o Stream da tabela e publica no bus; nenhum handler chama o EventBridge.
   Substitua pela entidade real, com o prefixo dela na auditoria
   (`audit_leading_keys` em `terraform-aws/iam.tf`, ADR-16); se ela precisar de slug/SKU únicos, veja o
   padrão de itens-ponteiro em
   `aws-megamix-app-lbd-catalog-service/docs/superpowers/specs`.
5. **API interna e eventos consumidos** — `src/service_template/audience.py`
   (distingue loja, portal e API interna pelos ids `STORE_API_ID`,
   `ADMIN_API_ID` e `INTERNAL_API_ID`) e `src/service_template/internal_api.py`
   (cliente SigV4 da API interna, usa `INTERNAL_API_ENDPOINT`); em
   `terraform-aws/internal_api.tf`, `internal_routes` (rotas internas que o
   serviço expõe, `AWS_IAM`) e `internal_api_calls` (rotas de outros serviços
   que ele chama, gera o `execute-api:Invoke`); em
   `terraform-aws/event_consumers.tf`, `event_consumers` (regra → fila SQS com
   DLQ e alarme → função). Os três mapas começam vazios.
6. **Contas AWS** — `terraform-aws/environments/dev.tfvars` e `prod.tfvars`.

Nenhuma dessas convenções é repetida aqui além do necessário para orientar a
adoção — a fonte é sempre `docs/arquitetura.md` e `docs/prd.md` do workspace
(`megamix-workspace`), e `.claude/rules/` para como trabalhar.

## Desenvolvimento local

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest --cov=service_template
```

Este template não tem conta AWS nem GitHub Environments configurados, então
o CI aqui só roda os testes Python (ver `TODO` em `.github/workflows/ci-dev.yml`).
Depois de configurar as Environments do serviço novo, reintroduza os jobs de
CI/CD de infraestrutura e nunca rode `terraform apply` localmente — a esteira
aplica em `dev` a cada push em `dev` e em `prod` a cada push em `main`.
