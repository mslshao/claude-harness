---
paths:
  - "src/python/**"
---

# Python Testing: Tenets, Mock Policy & Configuration

## Testing Tenets

Six tenets that govern testing decisions in gray areas. They don't cover every scenario,
but they resolve most "how should I test this?" questions. For the meta-rules that apply
these standards when the codebase shows conflicting patterns, see `tenets.md`.

### T1: Assert outcomes, not mechanics

Assert return values, state changes, and raised exceptions. Never assert call counts,
argument order, or internal wiring (`mock.assert_called_once_with`). A test that asserts
"S3 put_object was called with these args" breaks on any refactor that preserves behavior.
A test that puts an object and reads it back only breaks when behavior actually changes.
The former tests your implementation; the latter tests your contract.

### T2: Fake at the lowest layer

Moto intercepts at boto3. `responses` intercepts at `requests`. Let your real code
(serialization, error handling, retries) run against the fake. Do not mock a service
class three layers up to avoid an infrastructure call; every mocked layer is a layer
you are not testing.

When no infrastructure fake exists for an internal collaborator (it genuinely cannot
run in the test environment, not that it is inconvenient to set up), use `mockito`
(not `unittest.mock`): strict by default, fluent API, no string-based patching.
`mockito` is the escape hatch, not the default.

### T3: One test, one behavior, named to tell the story

Each test verifies a single observable behavior. Name it `test_<scenario>_<expected>`.
Use Arrange-Act-Assert. `test_expired_token_raises_auth_error` tells the next developer
exactly what broke when it fails at 2am in CI. `test_auth_flow` tells them nothing.
One behavior per test means one failure mode per test: self-diagnosing by design.

### T4: Tests are the spec; ship them with the code

Tests go in the same PR as the feature. Test names map to acceptance criteria. A new
developer should be able to read your tests and understand the system's contracts
without reading the implementation. "I'll add tests later" means tests will not be
added. Code without tests is a draft, not a deliverable. Tests outlive the author's
memory: six months from now, the tests are the only documentation guaranteed to be
accurate because they run.

### T5: Validate at the edge, trust the types inside

Test Pydantic validation at API boundaries. Do not re-assert field validation in every
unit test. Once data enters the system validated, trust the type system to carry
guarantees forward. Pydantic already tests Pydantic; your tests should exercise your
decisions (business rules, branching, error handling), not re-verify that your tools
work.

**Exception:** Custom validators (`@field_validator`, `@model_validator`) that encode
business rules ARE your logic. Test those: you are testing the business constraint,
not the framework.

**Litmus test:** If you deleted the code under test and the test still passed, you
were testing the framework, not your system.

### T6: Test the failure paths

For every feature, ask: what happens when this goes wrong? Test error conditions,
boundary values, timeouts, invalid input, and missing data. Name these tests explicitly:
`test_missing_document_raises_not_found`, `test_expired_session_returns_401`. Assert
specific exception types for exceptions your code defines. For error propagation through
layers you do not own, assert the observable outcome (status code, error response) instead.
The golden path is the easy part. Bugs live at the edges: the null that should not be
null, the timeout that was not handled, the race condition under load.

---

# Python Testing: Mock Policy & Configuration

## Mock Policy

**`unittest.mock` is banned.** Do not use `Mock`, `MagicMock`, `patch()`, `mocker.patch()`, or `create_autospec()` from `unittest.mock` anywhere in tests. Over 200 existing test files use `unittest.mock`; these predate the current policy and are tech debt, not precedent. Never use it in new tests. Use the appropriate mechanism for the boundary:

| Boundary | Fake mechanism | How to use |
|---|---|---|
| AWS (S3, DynamoDB, SQS, SNS, Secrets Manager, etc.) | **moto** - auto-activated globally via `mx2.testing.aws` | Use real boto3 clients. For DynamoDB, call `YourModel.create_table()` in fixtures (moto starts empty). |
| AWS error injection (force a `ClientError`/failure from a specific boto3 client mid-flow) | **botocore.stub.Stubber** on the client instance | Queue `add_response`/`add_client_error` in order; `assert_no_pending_responses()` on exit. Reference: `src/python/mx2/eventbridge/event_bridge_publisher_test.py`. Moto stays the default for happy-path AWS; Stubber is the error-injection seam. Do not stub the client object with mockito: it bypasses the botocore protocol layer and moto. |
| Sync HTTP (`requests`) | **pytest-responses** - global dev dependency | Use `responses` fixture to register URL/response pairs. |
| Async HTTP (`aiohttp`) | **aioresponses** | Use `aioresponses` fixture. `responses` does NOT intercept async HTTP. |
| Salesforce | **`FakeSalesforceManager`** from `mx2.testing.salesforce` | Routes calls to `https://fake.salesforce.com`, intercepted by `responses`. |
| LLM APIs (Anthropic, OpenAI, Bedrock; LangChain `init_llm` or raw SDK) | **`FakeChatModel` / `FakeOpenAIClient`** from `mx2.testing.llm` | Object-layer fakes: these SDKs are httpx/botocore-based, so `responses`/`respx` cannot intercept them, and there is no lower fake layer available. LangChain seam: `patch_init_llm(monkeypatch, fake_llm)`, then queue responses on `fake_llm`. Raw-SDK seam: the `fake_openai_client` fixture for `.chat.completions.create`/`.parse()`. Error factories (`openai_rate_limit_error()`, `anthropic_overloaded_error()`, etc.) return real vendor exception types, so no manual payload crafting. |

- **Stub at the lowest layer**: moto and pytest-responses are the correct stubbing boundary. Do not mock at higher abstraction layers (e.g., don't mock a service class to avoid an AWS or HTTP call).
- **`@responses.activate` is a trap in this repo; use the `responses` fixture.** The repo-global autouse `mock_aws` fixture layers moto's `RequestsMock` over pytest-responses' default mock. Under `@responses.activate`, registered stubs are still served (moto's registry consults the default mock), but the call log lands on moto's mock, so `responses.calls` is always empty: retry-count and request-URL assertions silently read zero and look like an interception failure. The pytest-responses `responses` fixture parameter patches topmost and records its own calls; it is the only shape that supports asserting on `responses.calls`. Canonical example: `src/python/mx2/sf_sync/client/sf_sync_client_test.py`.
- **Time determinism**: Use `freezegun` (`@freeze_time(...)`). Do not use `mockito` for this.
- **Internal collaborators (no infrastructure fake available)**: Use `mockito` (not `unittest.mock`). Fluent API, strict by default, no string-based patching. This is the escape hatch, not the default.
- **Environment/config stubbing**: Use pytest `monkeypatch` fixture for `setenv`/`setattr`. Use `Settings.set_for_testing()` for singleton Settings classes (see Configuration in Tests below).
- **Why this matters**: `unittest.mock` tests assert call order. Moto/responses tests assert outcomes. The former breaks on any refactor; the latter only breaks when behavior changes.
- **Serialization boundaries**: When models cross serialization boundaries (EventBridge, SQS, HTTP APIs), test that JSON-safe dumps (`model.model_dump(mode="json")` or `model.model_dump_json()`) round-trip correctly and can be reconstructed into the original model type.

## Configuration in Tests

Settings classes inherit from `Singleton` (`mx2.objects.singleton`). Separate env setup from Settings instantiation:

```python
@pytest.fixture(name="env")
def fixture_env(monkeypatch):
  """Set environment variables for Settings instantiation."""
  monkeypatch.setenv("WORKSPACE", "test")
  monkeypatch.setenv("TABLE_NAME", "test-table")


@pytest.fixture(name="settings")
def fixture_settings(env):
  """Provide test Settings instance with lifecycle management."""
  with AppSettings.set_for_testing() as instance:
    yield instance
```
