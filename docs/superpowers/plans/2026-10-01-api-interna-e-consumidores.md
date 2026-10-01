# Template: público por apiId, cliente da API interna e consumidores — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** dar a todo serviço novo o resolvedor de público por `apiId` (ADR-24), o cliente SigV4 da API interna (ADR-29) e o Terraform de rota interna e de consumidor de eventos (ADR-27).

**Architecture:** dois módulos Python sem dependência de terceiros (`botocore` do runtime para assinar, `urllib.request` para enviar) e dois arquivos Terraform: `internal_api.tf` comentado como exemplo e `event_consumers.tf` dirigido por um mapa vazio.

**Tech Stack:** Python 3.12, Powertools, pytest + moto, Terraform.

**Spec:** `docs/superpowers/specs/2026-09-27-tpl-app-aws-lbd-python-design.md` §2 (linhas de `audience.py`, `internal_api.py`, `internal_api.tf`, `event_consumers.tf` e testes).

## Global Constraints

- Repositório público: nada da Mega Mix; prefixo do produto como `<product>`/`local.product` com `TODO`
- Sem dependência nova no zip (só stdlib, `boto3`/`botocore` do runtime e Powertools da layer)
- Timeout do cliente: 3 s; **uma** nova tentativa só em erro de rede ou `5xx`
- Erro da API no formato do ADR-19 (`{"error": {"code", "message"}}`); corpo fora do formato vira `code = "UNKNOWN"`
- Cobertura ≥ 80%

## Review Focus

- `INTERNAL_API_ENDPOINT` com barra no fim e caminho com barra no começo: URL sem `//`
- Query string com vírgulas (`?ids=a,b`): a assinatura SigV4 tem de cobrir a query exatamente como enviada
- `4xx` nunca é repetido (o chamador decide; `404` é resposta, não falha)
- Resposta `204` sem corpo devolve `None`, sem erro de JSON
- `apiId` presente mas variável de ambiente vazia (serviço que não usa aquela API) → `403`, nunca casa com string vazia

---

### Task 1: `audience.py`

**Files:**
- Create: `src/service_template/audience.py`
- Test: `tests/test_audience.py`

**Interfaces:**
- Produces: `Audience = Literal["store", "admin", "internal"]`; `audience(event: dict) -> Audience` (lança `ForbiddenError`)

- [ ] **Step 1: Testes que falham**

```python
@pytest.mark.parametrize("api_id,expected", [("store1", "store"), ("admin1", "admin"), ("int1", "internal")])
def test_resolves_audience_by_api_id(monkeypatch, api_id, expected):
    monkeypatch.setenv("STORE_API_ID", "store1"); monkeypatch.setenv("ADMIN_API_ID", "admin1"); monkeypatch.setenv("INTERNAL_API_ID", "int1")
    assert audience({"requestContext": {"apiId": api_id}}) == expected

def test_unknown_api_id_is_forbidden(monkeypatch): ...      # apiId "outra" → ForbiddenError
def test_empty_env_never_matches(monkeypatch): ...          # INTERNAL_API_ID="" e apiId "" → ForbiddenError
def test_missing_request_context_is_forbidden(): ...        # {} → ForbiddenError
```

- [ ] **Step 2:** `pytest tests/test_audience.py -v` → FAIL (módulo inexistente)
- [ ] **Step 3:** implementar `audience(event)` lendo as três variáveis a cada chamada (testes trocam o ambiente); valores vazios ignorados; mensagem do `ForbiddenError`: "Você não tem permissão para esta ação."
- [ ] **Step 4:** `pytest tests/test_audience.py -v` → PASS
- [ ] **Step 5:** `git commit -m "feat: publico da requisicao pelo apiId (ADR-24)"`

### Task 2: `internal_api.py`

**Files:**
- Create: `src/service_template/internal_api.py`
- Test: `tests/test_internal_api.py`

**Interfaces:**
- Produces:
  - `class InternalApiError(Exception)`: atributos `status: int`, `code: str`, `message: str`
  - `class DependencyUnavailable(Exception)`
  - `class InternalApiClient(endpoint: str | None = None, *, timeout: float = 3.0, transport: Callable[[Request, float], tuple[int, bytes]] | None = None, credentials=None, region: str | None = None)`; `endpoint` padrão = `os.environ["INTERNAL_API_ENDPOINT"]`
  - `InternalApiClient.request(method: str, path: str, *, query: dict[str, str] | None = None, body: dict | None = None, correlation_id: str = "") -> dict | None` — devolve o JSON da resposta `2xx` (`None` em `204`); `4xx` → `InternalApiError`; rede/`5xx` duas vezes → `DependencyUnavailable`

- [ ] **Step 1: Testes que falham** (transporte falso que registra as requisições e devolve respostas programadas; credenciais `botocore.credentials.Credentials("AKID", "SECRET")`, região `sa-east-1`)

```python
def test_signs_request_with_sigv4(): ...            # header Authorization começa com "AWS4-HMAC-SHA256" e cita "execute-api"
def test_joins_endpoint_and_path_without_double_slash(): ...  # endpoint "https://x/" + "/catalog/products" → "https://x/catalog/products"
def test_query_is_sent_and_signed(): ...            # query {"ids": "a,b"} → URL termina com "?ids=a%2Cb" e a assinatura foi calculada sobre ela
def test_propagates_correlation_id(): ...           # header "X-Correlation-Id" = "c-1"
def test_returns_json_on_2xx_and_none_on_204(): ...
def test_4xx_raises_with_code_and_is_not_retried(): ...       # 404 {"error":{"code":"NOT_FOUND","message":"x"}} → InternalApiError(status=404, code="NOT_FOUND"); 1 chamada
def test_4xx_outside_contract_has_unknown_code(): ...
def test_retries_once_on_5xx_then_succeeds(): ...   # 503 depois 200 → 2 chamadas, devolve o JSON
def test_network_error_twice_raises_dependency_unavailable(): ...  # transporte lança URLError duas vezes
def test_timeout_passed_to_transport(): ...         # 3.0
```

- [ ] **Step 2:** `pytest tests/test_internal_api.py -v` → FAIL
- [ ] **Step 3:** implementar: `botocore.awsrequest.AWSRequest` + `botocore.auth.SigV4Auth(credentials, "execute-api", region)` (credenciais padrão de `boto3.Session().get_credentials()`, região de `AWS_REGION`); `transport` padrão envia por `urllib.request.urlopen(req, timeout=timeout)` e devolve `(status, corpo)`, tratando `HTTPError` como resposta; `Content-Type: application/json` quando houver corpo
- [ ] **Step 4:** `pytest tests/test_internal_api.py -v` → PASS
- [ ] **Step 5:** `git commit -m "feat: cliente SigV4 da API interna (ADR-29)"`

### Task 3: Terraform de rota interna e de consumidores

**Files:**
- Create: `terraform-aws/internal_api.tf`
- Create: `terraform-aws/event_consumers.tf`
- Create: `terraform-aws/iam_templates/policies/lambda_internal_api_policy.tftpl`
- Create: `terraform-aws/iam_templates/policies/lambda_sqs_consumer_policy.tftpl`
- Modify: `terraform-aws/data.tf`, `terraform-aws/lambda.tf` (variáveis `STORE_API_ID`, `ADMIN_API_ID`, `INTERNAL_API_ID`, `INTERNAL_API_ENDPOINT`), `README.md`

**Interfaces:**
- Produces:
  - `local.internal_routes` (mapa `"MÉTODO /caminho" => chave da função`, vazio) com `aws_apigatewayv2_route.internal` (`authorization_type = "AWS_IAM"`) e integração/permissão no `execution-arn` interno
  - `local.internal_api_calls` (mapa `chave da função => ["MÉTODO /caminho", ...]`, vazio) gerando a política `execute-api:Invoke` em `<execution-arn>/$default/<MÉTODO>/<caminho com {param} trocado por *>`
  - `local.event_consumers` (mapa `nome => {function, sources, detail_types, pattern_extra = optional}`, vazio): regra, fila `"${local.product}-${local.service}-${nome}"`, DLQ (`maxReceiveCount = 3`), `aws_lambda_event_source_mapping` com `function_response_types = ["ReportBatchItemFailures"]`, alarme `ApproximateNumberOfMessagesVisible > 0` na DLQ

- [ ] **Step 1:** escrever os dois `.tf` com os mapas vazios e comentários `TODO` mostrando um exemplo de cada; data sources `/<product>/apigw/internal/api/{id,execution-arn,endpoint}` e as dos ids das APIs da loja e do portal
- [ ] **Step 2:** `cd terraform-aws && terraform fmt -check && terraform init -backend=false && terraform validate` → sem erro
- [ ] **Step 3:** README: ordem de preenchimento dos `TODO` cita `audience.py`, `internal_api.py`, `internal_routes`, `internal_api_calls` e `event_consumers`
- [ ] **Step 4:** `git commit -m "feat: rota interna e consumidores de eventos no template"`

### Task 4: PR

- [ ] `pytest --cov` ≥ 80%; `revisor-pr`; push; `gh pr create --base dev --title "feat: publico por apiId, cliente da API interna e consumidores no template"`
- [ ] CI verde; merge em `dev` com autorização do usuário; `dev` → `main` pelo usuário. Serviços existentes copiam os módulos novos (o template não é dependência)
