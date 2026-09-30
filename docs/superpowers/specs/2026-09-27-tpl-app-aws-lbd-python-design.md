# Template de serviço Lambda Python — Design

**Data:** 2026-09-27
**Status:** Aprovado
**Repositório:** `tpl-app-aws-lbd-python` (novo, público)

## 1. Propósito e escopo

Extração do template de serviço (ADR-12), agora que o primeiro serviço de
domínio (`aws-megamix-app-lbd-catalog-service`) estabilizou em produção
(v1.0.0). Cobre só o scaffolding transversal para criar um serviço Lambda
Python novo: infraestrutura Terraform (ADR-04, ADR-09, ADR-10), esteira de
testes (CI), e os módulos Python de infraestrutura comuns a qualquer serviço
de domínio.

Por ser um repositório público (`tpl-*`), não tem nenhuma regra de negócio,
nome de entidade ou dado da Mega Mix (`.claude/rules/seguranca.md` #3) — só o
nome da organização/produto como branding de repositório, documentado como
ponto de ajuste.

**Mecanismo de adoção:** GitHub template repository ("Use this template").
Sem geração por placeholders (cookiecutter/copier) — simplicidade, sem
dependência nova para um projeto de um único desenvolvedor. Todo ponto que o
novo serviço precisa trocar ou completar é marcado com comentário `TODO` no
próprio arquivo.

**Fora de escopo:**
- CI/CD de infraestrutura (Terraform) contra uma conta AWS real — o template
  não tem GitHub Environments nem conta configurados; os workflows
  `ci-infra-terraform.yml`/`cd-infra-terraform.yml` (`shd-github-actions-workflows`)
  ficam como `TODO` para o serviço novo reintroduzir depois de configurar as
  Environments (ADR-08)
- Qualquer código de domínio (modelos, repositório com padrão de
  itens-ponteiro, validação de campos de negócio) — só a estrutura e um
  exemplo mínimo

## 2. Estrutura extraída

Do `aws-megamix-app-lbd-catalog-service`:

| Origem | Destino no template | Tratamento |
| --- | --- | --- |
| `terraform-aws/{provider,variables,data}.tf` | idem | cópia direta, já genéricos |
| `terraform-aws/iam_templates/**` | idem | cópia direta, já genéricos |
| `terraform-aws/locals.tf` | idem | `service`/`repository` viram `TODO` |
| `terraform-aws/dynamodb.tf` | idem | tabela genérica com 1 GSI de exemplo, `TODO` para ajustar aos padrões de acesso reais |
| `terraform-aws/iam.tf` | idem | `lambda_functions` do exemplo `hello`; `TODO` na fonte do módulo `iam-role` (ainda não existe em `shd-terraform-aws-modules`) |
| `terraform-aws/lambda.tf`, `api.tf` | idem | nomes/rotas do exemplo `hello`, com `TODO` apontando o que trocar |
| `terraform-aws/environments/*.tfvars` | idem | `aws_account_id` vira placeholder `000000000000` |
| `.github/workflows/ci-{dev,prod}.yml` | idem | mantém `pr-validation` + testes Python; job de CI de infraestrutura removido (ver fora de escopo) |
| `.github/workflows/release.yml` | idem | cópia direta (ADR-14 vale para todo repo) |
| `.pipeline.yml`, `pytest.ini`, `requirements-dev.txt`, `.gitignore` | idem | cópia direta |
| `src/catalog_service/{http,errors,ids,auth}.py` | `src/service_template/*` | cópia direta, só o prefixo de import muda |
| `src/catalog_service/observability.py` | idem | nome do serviço vira `TODO` |
| `src/catalog_service/events.py` | idem | `strip_internal_keys`/`normalize_number` migram para `dynamo.py` (não dependem de domínio); `Source` do evento vira `TODO` |
| `src/catalog_service/validation.py` | idem | só os helpers primitivos (`require_object`, `required_str`, `optional_str`, `optional_id`, `slug`); os `*_fields` de produto/categoria/marca ficam de fora |
| `src/catalog_service/handlers/brands_{read,write}.py` | `handlers/hello_manager.py` | vira o exemplo ponta a ponta, uma função por recurso com leitura e escrita juntas: rota → autorização de grupo → validação → acesso à tabela (`boto3` direto, sem `repository.py`) → resposta HTTP → evento de domínio |
| `tests/{conftest,test_http,test_ids,test_auth}.py` | idem | cópia/adaptação direta |
| `tests/test_observability.py`, `test_events.py` | idem | adaptados ao nome genérico do serviço |
| `tests/handlers/{api_events,test_brands_*}.py` | `tests/handlers/{api_events,test_hello_*}.py` | `api_events.py` cópia direta; testes do exemplo `hello` cobrindo o caminho feliz, 403 e 400 |

Não entram: `models.py`, `repository.py`, `filtering.py` (domínio real de
produtos/categorias/marcas) e os testes correspondentes.

## 3. Adoção, documentação e critério de pronto

- Repositório marcado como **template repository** nas Settings do GitHub
  após o merge em `main`.
- `README.md` lista a ordem sugerida de preenchimento dos `TODO`s e aponta
  para `docs/arquitetura.md`/`docs/prd.md` do workspace e para a spec do
  catalog-service como referência de padrões não copiados aqui (ex.: itens-
  ponteiro para unicidade de slug/SKU).
- Critério de saída: repositório criado, testes do exemplo `hello` passando
  localmente com cobertura ≥ 80% (RNF-10), marcado como template no GitHub.
