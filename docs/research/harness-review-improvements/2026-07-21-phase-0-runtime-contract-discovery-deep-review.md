# Deep Research/Review: Phase 0 — Runtime Contract và Discovery

> **Ngày:** 2026-07-21  
> **Trạng thái:** Research / design review, chưa triển khai  
> **Parent:** [`docs/research/harness-review-improvements/research-local-runtime-for-agentic-debugging.md`](research-local-runtime-for-agentic-debugging.md)

## 1. Executive summary

Phase 0 không nên được xem là “thêm một file YAML để chứa vài command”. Nó là việc định nghĩa một **contract an toàn giữa project, harness, runtime adapter và AI agent**.

Khuyến nghị sau review:

1. Tách ba lớp dữ liệu: declared contract, discovery report và resolved runtime model.
2. Discovery chỉ tạo candidate và warning; không tự cấp quyền mutation.
3. Dùng logical service name làm lớp ổn định; mapping xuống Docker Compose service là implementation detail.
4. Không cho contract chứa arbitrary shell command ở Phase 0. Contract tham chiếu semantic operation và test target đã đăng ký.
5. Resolve Docker Compose bằng chính Compose CLI (`docker compose config --format json`), không tự viết lại Compose parser. Lệnh này render model canonical, merge file và resolve interpolation. [Compose config reference](https://docs.docker.com/reference/cli/docker/compose/config/)
6. `.harness/runtime.yaml` tốt cho UX, nhưng parser strategy phải được chốt trước khi code. Nếu muốn giữ stdlib-only như `harness-manifest.json`, JSON là lựa chọn đơn giản hơn.
7. Phase 0 chỉ hoàn tất khi discovery deterministic, có provenance, conflict handling, secret-safe output và fixture tests.

## 2. Câu hỏi Phase 0 phải trả lời

| Câu hỏi | Kết quả cần có |
|---|---|
| Runtime nào đang được dùng? | `docker-compose`, `native`, `unknown` |
| Source of truth ở đâu? | path cụ thể và hash |
| Project identity là gì? | root, project name, environment label |
| Service nào tồn tại? | logical name, runtime name, profile, state |
| Service nào agent được phép quan sát? | capability rõ ràng |
| Service nào được phép mutate? | allowlist và approval policy |
| Làm sao biết service ready? | healthcheck/readiness hoặc `unknown` |
| Test/smoke check nào chạy được? | registered target và provenance |
| Điều gì chưa biết? | warnings, conflicts, unsupported features |

Discovery thành công không có nghĩa runtime an toàn để điều khiển; chỉ có nghĩa harness hiểu đủ context để quyết định bước tiếp theo.

## 3. Boundary và thuật ngữ

### Declared contract

File do project owner commit, ví dụ `.harness/runtime.yaml`. Nó khai báo runtime kind, Compose files/profile/project name, logical services, healthchecks, verification targets, policy và redaction rules. Contract có thể outdated, nên phải đối chiếu với runtime thực tế.

### Discovery

Quá trình read-only tìm evidence từ filesystem và runtime CLI: Compose files, manifests, process listeners, Compose project/service list, health metadata và test runner declarations. Discovery output không phải instruction và không tự động là permission.

### Resolved runtime model

Model canonical kết hợp contract, discovered evidence và runtime state. Chỉ model đã validate mới được đưa vào runtime adapter.

```text
declared contract + discovery + runtime observation
              │
              ▼
validation + precedence + conflict handling
              │
              ▼
resolved model → read-only capabilities / gated mutations
```

### Logical service và runtime service

`api` là logical service. Nó có thể map tới Compose service `backend`, native process `uvicorn`, hoặc Make target. Agent dùng logical name; adapter giữ mapping runtime-specific.

### Configuration và runtime state

Configuration nói cách runtime nên được điều khiển. State nói runtime hiện tại ra sao. Không ghi runtime state ngược vào contract.

## 4. Docker Compose constraints

### Multiple files và project model

Compose có `compose.yaml`, `compose.yml`, override files, `-f`, `COMPOSE_FILE`, profiles, `include` và `extends`. Nhiều file được merge theo thứ tự; path trong model merge được resolve theo base file. [Application model](https://docs.docker.com/compose/intro/compose-application-model/), [merge files](https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/)

Discovery phải lưu:

```text
selected compose files
selection source
project directory
env-file selection
active profiles
project name
resolved model hash
```

Không đủ an toàn nếu chỉ tìm `compose.yaml` rồi parse danh sách services.

### Interpolation và environment

Compose hỗ trợ `${VAR}`, default/required expression và `$$`; interpolation diễn ra trước merge theo từng file. Biến unresolved có thể tạo warning và thành empty string. [Interpolation](https://docs.docker.com/reference/compose-file/interpolation/)

`.env`, shell environment, `--env-file`, `environment`, `env_file` và CLI có precedence khác nhau. [Environment precedence](https://docs.docker.com/compose/how-tos/environment-variables/envvars-precedence/)

Hệ quả:

- model trên disk chưa chắc là model runtime nhìn thấy;
- raw `docker compose config` có thể chứa secret;
- discovery phải dùng canonical Compose model nhưng redact trước khi trả cho model hoặc lưu artifact.

### Project name và isolation

Project name ảnh hưởng container/resource names và isolation. Precedence gồm `-p`, `COMPOSE_PROJECT_NAME`, top-level `name`, thư mục chứa Compose file và current directory. [Project name](https://docs.docker.com/compose/how-tos/project-name/)

Worktree/branch có thể va chạm nếu dùng directory basename. Phase 0 phải report project name và cảnh báo nếu identity không ổn định; không tự đổi name nếu chưa có explicit policy.

### Profiles và active graph

Service có profile có thể không active. Service được target trực tiếp có thể activate profile; dependency giữa profile không tương thích có thể làm model invalid. [Profiles](https://docs.docker.com/reference/compose-file/profiles/)

Report phải phân biệt:

```text
declared service: debug-ui
profile: debug
active now: false
available with profile=debug: true
capability: observe=false until explicitly selected
```

### Healthcheck và readiness

Compose healthcheck là command xác định container health; `depends_on: condition: service_healthy` có thể chờ dependency healthy. Nhưng container health không nhất thiết là business readiness. [Compose services](https://docs.docker.com/reference/compose-file/services/), [Compose specification](https://compose-spec.github.io/compose-spec/spec.html)

Contract nên phân biệt:

```text
container_health → Docker health status
service_ready    → service-level readiness
application_smoke → HTTP/CLI business check
```

Nếu chỉ có container health, output phải ghi `readiness_level: container`, không gọi là application healthy.

### Canonical resolution

`docker compose config --format json` là nguồn resolved model: merge files, resolve variables và expand short notation. Adapter không nên tái triển khai Compose merge/interpolation bằng regex hoặc parser riêng.

## 5. Contract design review

### Option A — Arbitrary command

```yaml
services:
  api:
    logs:
      command: docker compose logs api
    test:
      command: docker compose exec api pytest
```

Linh hoạt nhưng biến config thành shell execution surface; khó allowlist, dễ injection, khó port sang native runtime. **Không khuyến nghị cho v1.**

### Option B — Semantic targets

```yaml
services:
  api:
    runtime_name: api
    observe: true
    health:
      probes:
        - id: http-health
          type: http
          url: http://127.0.0.1:8000/health
          expected_status: 200
    verification:
      - id: auth-tests
        runner: pytest
        selector: tests/auth/
```

Adapter chọn command an toàn cho status/logs/health/verify. Portable, validate được và dễ cấp capability; đổi lại cần extension cho edge case. **Khuyến nghị cho v1.**

### Option C — Semantic core + custom operation gated

Cho phép custom operation chỉ khi có id ổn định, `read_only`, timeout/output limit, argv array thay vì shell string, approval cho mutation và fixture test. **Phù hợp sau MVP, không phải default.**

## 6. YAML hay JSON?

### YAML

Dễ đọc, hợp config DevOps, hỗ trợ comment; nhưng cần parser dependency và phải kiểm soát duplicate keys, aliases, anchors và implicit typing.

### JSON

Parser stdlib, semantics ít mơ hồ, phù hợp tooling hiện tại và `harness-manifest.json`; nhưng verbose và không có comment native.

JSON Schema 2020-12 là meta-schema hiện hành, nhưng JSON Schema không tự parse YAML; đây là hai concerns khác nhau. [JSON Schema specification](https://json-schema.org/specification)

### Recommendation

Chốt parser strategy trước khi triển khai. Nếu không muốn thêm dependency cho harness, dùng JSON. Nếu giữ `.harness/runtime.yaml`, phải ghi rõ parser, version, duplicate-key behavior và test contract.

## 7. Proposed contract v1

```yaml
version: 1
runtime:
  kind: docker-compose
  compose:
    files: [compose.yaml, compose.override.yaml]
    project_directory: .
    project_name: null
    profiles: []

services:
  api:
    runtime_name: api
    role: application
    observe: true
    mutate: false
    health:
      container: true
      probes:
        - id: http-health
          type: http
          url: http://127.0.0.1:8000/health
          expected_status: 200
          timeout: 5s
    verification:
      - id: unit
        runner: pytest
        selector: tests/api/
        read_only: true

policies:
  default_capability: observe
  allow_restart: [api]
  approval_required: [exec, start, stop, database-mutation]
  limits:
    log_lines: 500
    output_bytes: 200000
    command_timeout: 60s

redaction:
  env_names: ['*TOKEN*', '*PASSWORD*', '*SECRET*', '*PRIVATE_KEY*']
```

Schema rules:

- `version` bắt buộc và chỉ nhận version đã biết;
- runtime kind là enum; `unknown` chỉ là discovery state, không phải adapter;
- paths relative tới root/project directory; reject escape như `../../prod`;
- service names và runtime names không chứa shell metacharacters;
- HTTP probe chỉ local scope trong MVP;
- selector không biến thành raw shell string;
- `mutate: true` không bypass approval;
- limits có upper bound;
- unknown keys phải reject hoặc nằm trong explicit `extensions`, không silently ignore.

## 8. Precedence và conflict handling

Đề xuất thứ tự từ authoritative đến heuristic:

1. Explicit invocation flags.
2. Committed runtime contract.
3. Canonical Compose model.
4. Runtime observation.
5. Repository conventions.
6. Filename/script heuristics.

Rules:

- contract xác nhận intended mapping, không xác nhận service đang healthy;
- runtime model xác nhận service tồn tại, không cấp mutation permission;
- heuristic chỉ tạo candidate;
- conflict giữa explicit contract và runtime là `error` hoặc `needs_review`, không silent override;
- missing signal là `unknown`, không phải `false`.

Ví dụ:

```text
contract: api -> backend
compose services: [api, db]
result: error — declared runtime_name backend not found
```

```text
contract: api.observe = true
runtime: api container absent
result: capability observe=true, state=absent
```

## 9. Discovery algorithm

### Step 0 — Root

- nhận root explicit;
- canonicalize path và symlink;
- reject `/`, home hoặc broad unsafe target;
- xác nhận `.git`/project marker;
- không scan parent ngoài scope nếu chưa bật.

### Step 1 — Contract

- tìm `.harness/runtime.yaml` hoặc `.harness/runtime.json`;
- nếu cả hai tồn tại mà chưa có precedence, fail;
- parse, schema validate, lưu source/hash/parser version.

### Step 2 — Candidates

Deterministic order: explicit contract → `compose.yaml` → `compose.yml` → `docker-compose.yml` → `docker-compose.yaml` → known native manifests/scripts → unknown. Không scan mọi YAML vì có thể nhầm Kubernetes/CI fixture.

### Step 3 — Resolve Compose

- lấy file list từ contract hoặc explicit invocation;
- resolve project directory/profile/env policy;
- chạy `docker compose ... config --format json`;
- capture exit code, stderr warning, Compose version và model hash;
- không lưu expanded secret values;
- tách declared, active và profile services.

### Step 4 — Observe state

- `docker compose ps --all --format json` nếu available;
- fallback parser chỉ khi cần và phải warning;
- lấy health/status/restart count;
- không chạy `logs --follow` trong discovery;
- logs chỉ tail bounded sample khi caller yêu cầu.

### Step 5 — Map services

- explicit mapping thắng heuristic;
- exact name match confidence cao nhưng ghi provenance;
- role guesses (`api`, `web`, `db`, `worker`) chỉ là candidate;
- ambiguous mapping là `needs_review`;
- profile inactive không phải running/usable.

### Step 6 — Emit

```text
discovery-report.json  # evidence, warnings, candidates, provenance
resolved-runtime.json  # validated model and gated capabilities
```

Resolved output không chứa raw environment, token, secret hoặc full unredacted config.

## 10. Confidence và provenance

Mỗi fact cần source, method, confidence và timestamp:

```json
{
  "value": "api",
  "source": ".harness/runtime.yaml:services.api.runtime_name",
  "method": "explicit",
  "confidence": 1.0,
  "observed_at": "2026-07-21T10:00:00Z"
}
```

Confidence chỉ giúp orchestration, không tự cấp quyền:

| Signal | Confidence | Sử dụng |
|---|---:|---|
| explicit contract | 1.0 | dùng sau schema/policy validation |
| exact runtime match | 0.9 | read-only; mutation vẫn cần policy |
| role heuristic | 0.6 | đề xuất / needs review |
| filename/script guess | <0.6 | không executable |

“Không quan sát được” phải là `unknown`; không có kết quả không chứng minh “không tồn tại”.

## 11. Capability model

Không map `observe: true` thành shell tổng quát. Capability nên granular:

```text
service.api.logs
service.api.status
service.api.healthcheck
service.api.exec.readonly
service.api.restart
project.start
project.stop
project.database_mutation
```

Mỗi capability có subject, operation, read-only/mutating, source, approval, timeout/output limit và audit requirement. Default nên là observe-only; `down -v` và volume/database destruction hard-block trong MVP.

## 12. Environment và secret handling

Không gửi raw `docker compose config`, không chạy `docker compose exec env` mặc định, không đưa `.env` contents vào report. Chỉ emit variable names/presence marker khi cần, mask values và hỗ trợ project redaction patterns. Docker cũng khuyến nghị cẩn trọng với sensitive data trong environment và cân nhắc Secrets. [Environment best practices](https://docs.docker.com/compose/how-tos/environment-variables/best-practices/)

Redaction cần test cả:

- `TOKEN`, `PASSWORD`, `SECRET`, `PRIVATE_KEY`;
- URL chứa credential;
- JSON log fields;
- multiline private keys;
- ANSI/control characters;
- secret bị split qua nhiều dòng.

## 13. Native process discovery

Native adapter là phase sau; Phase 0 chỉ report candidate từ `package.json`, `pyproject.toml`, `Makefile`, `Procfile`, README và listening ports.

Một script tên `dev` không mặc nhiên là start command an toàn:

```text
candidate: npm run dev
source: package.json:scripts.dev
confidence: 0.8
executable: false
reason: no explicit runtime contract permission
```

Native runtime còn có process group, child process, signal forwarding, port collision, PID reuse, cwd, environment, TTY và cleanup. Vì vậy chưa auto-start process ở Phase 0.

## 14. Failure modes

| Failure | Required behavior |
|---|---|
| Không tìm thấy contract | `unknown`, không mutate |
| Có cả YAML và JSON | fail validation |
| Compose invalid | stop before capability issuance |
| Missing required env | preserve warning/error |
| Service mapping mismatch | hard validation error |
| Multiple Compose candidates | `needs_review` |
| Profile inactive | `inactive`, không readiness claim |
| Healthcheck thiếu | `readiness=unknown` |
| Project-name collision risk | warning hoặc explicit name required |
| Secret trong output | redact + audit |
| Unsupported Compose feature | fail closed for mutation |
| Docker unavailable | config discovery có thể pass; state unknown |

## 15. Testing strategy

### Schema tests

Test minimal valid contract, every runtime kind, unknown version/key, path traversal, invalid service name, invalid URL scope, invalid limits và mutation thiếu approval.

### Discovery fixtures

| Fixture | Expected result |
|---|---|
| only `compose.yaml` | one deterministic candidate |
| base + override | selected files và provenance đúng |
| profiles | inactive services không healthy |
| explicit mapping mismatch | validation error |
| exact mapping | high-confidence mapping |
| ambiguous api/backend | needs review |
| missing `.env` variable | warning/error preserved |
| secret-like values | redacted output |
| invalid Compose | no executable model |
| Docker unavailable | runtime state unknown |
| native-only repo | candidate report, no auto-start |

### Golden output

Snapshot normalized model, không snapshot container ID, timestamp, log order hoặc các volatile fields. Tách deterministic model, volatile observation và invocation metadata.

### Drift tests

CI nên kiểm tra schema version có parser, verification runner có adapter, service mapping tồn tại trong canonical model, docs/schema không drift và fixture secret không lọt ra output.

## 16. Discovery observability

Report phải giải thích vì sao chọn model nào:

```json
{
  "schema_version": 1,
  "runtime_kind": "docker-compose",
  "sources": [
    {"path": ".harness/runtime.yaml", "kind": "declared", "sha256": "..."},
    {"path": "compose.yaml", "kind": "compose-input", "sha256": "..."}
  ],
  "decisions": [
    {"field": "services.api.runtime_name", "value": "api", "source": "explicit", "confidence": 1.0}
  ],
  "warnings": [],
  "capabilities": [],
  "redactions": {"count": 3}
}
```

Agent phải biết source, age, confidence và warnings của model; không nhận một model opaque.

## 17. Decisions cần chốt trước khi code

1. **File format:** JSON nếu zero dependency là ưu tiên; YAML nếu parser policy được ghi rõ.
2. **Raw commands:** không có trong core v1; semantic targets trước.
3. **Authority:** explicit contract > canonical model > runtime state > convention > heuristic.
4. **Compose parsing:** delegate cho `docker compose config --format json`.
5. **Scope:** Compose discovery/model trước; native chỉ report candidate.
6. **Capability:** observe-only mặc định; mutation explicit + audit; `down -v` hard-block.
7. **Evidence:** `specs/<slug>/runtime/` khi gắn task; không secret; generated output không thay contract.

## 18. Deliverables đề xuất

```text
.harness/runtime.schema.json       # hoặc schema tương đương
scripts/runtime-discover.py        # read-only discovery
scripts/runtime-validate.py        # schema + semantic validation
scripts/runtime-normalize.py       # canonical model
templates/runtime-contract.yaml
tests/runtime/fixtures/
```

Logic parsing/hashing/JSON nên nằm trong Python; Bash wrapper chỉ giữ invocation và exit-code contract.

## 19. Acceptance criteria

Phase 0 đạt khi:

1. Có schema versioned và parser strategy được ghi rõ.
2. Discovery chạy read-only trên fixture repo.
3. Compose model lấy từ `docker compose config --format json`.
4. Selected files, project directory, profile và project name có provenance.
5. Contract mismatch tạo lỗi rõ ràng, không tự sửa config.
6. Mapping phân biệt logical name, runtime name và active state.
7. Thiếu healthcheck cho `readiness=unknown`.
8. Report không chứa raw secret values.
9. Heuristic discovery không cấp mutation capability.
10. Có fixtures cho override, profile, interpolation failure, missing runtime, ambiguity và redaction.
11. Normalized model deterministic.
12. Agent biết khi nào `proceed`, `needs_review` hoặc `blocked`.

## 20. Kết luận review

Phase 0 nên tối ưu cho **giải thích được, deterministic và fail-closed ở capability boundary**, không phải coverage mọi loại project.

```text
AI biết runtime nào tồn tại,
biết điều gì đã được xác nhận,
biết điều gì chỉ là phỏng đoán,
biết service nào đang active,
và bị chặn trước mutation chưa được cấp quyền.
```

Nếu các boundary này được chốt trước, những phase sau có thể thêm logs, exec, restart và automated verification mà không biến harness thành một shell-access layer khó kiểm soát.

## 21. References

- [Docker Compose file reference](https://docs.docker.com/reference/compose-file/)
- [Compose application model](https://docs.docker.com/compose/intro/compose-application-model/)
- [Docker Compose config CLI](https://docs.docker.com/reference/cli/docker/compose/config/)
- [Merge Compose files](https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/)
- [Compose interpolation](https://docs.docker.com/reference/compose-file/interpolation/)
- [Compose services and healthcheck](https://docs.docker.com/reference/compose-file/services/)
- [Compose profiles](https://docs.docker.com/reference/compose-file/profiles/)
- [Compose project name](https://docs.docker.com/compose/how-tos/project-name/)
- [Compose environment precedence](https://docs.docker.com/compose/how-tos/environment-variables/envvars-precedence/)
- [Compose environment best practices](https://docs.docker.com/compose/how-tos/environment-variables/best-practices/)
- [JSON Schema specification](https://json-schema.org/specification)
