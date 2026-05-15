# Test Constraints

Copy these verbatim into the test-generator agent prompt.

```
CONSTRAINTS: read these before writing any test.
These constraints OVERRIDE the test-generator's own system prompt where they conflict.

- Every test must verify a DOMAIN BEHAVIOR, not a framework mechanic. Do not test
  that Pydantic models serialize/deserialize. Do not test that FastAPI returns JSON.
  Do not test that pytest fixtures work. Test what THIS code does that no other code does.

- Assertions must target OUTCOMES, not call patterns. Assert the return value, the
  state change, the raised exception with its context. Do NOT assert mock.called_once_with()
  unless the call itself IS the behavior being tested (e.g., "audit event was logged").

- DO NOT use unittest.mock (Mock, patch, MagicMock) for AWS or HTTP. moto is enabled
  globally (all boto3 calls are auto-faked) and pytest-responses is enabled globally
  (all `requests` library calls are auto-faked). Use real boto3 clients in your tests
  and in the system-under-test. If you feel you need a Mock, that's a signal the code
  may need refactoring, not that the test needs more mocks.

- For sync HTTP via `requests`: use the `responses` fixture to register expected
  call/response pairs:
    def test_fetches_document(self, responses):
        responses.get("https://api.example.com/doc/123", json={"id": "123"})
        result = fetch_document("123")
        assert result.id == "123"

- For async HTTP via `aiohttp`: use `aioresponses` (not `responses`).
  The `responses` library does NOT intercept async HTTP.

- FastAPI TestClient calls (via httpx) do NOT go through `requests`; they don't
  need `responses` registration. Only outbound HTTP calls FROM your handlers need it.

- For Salesforce: use the `FakeSalesforceManager` fixture from `mx2.testing.salesforce`.
  It routes API calls to `https://fake.salesforce.com`, intercepted by `responses`.
  Do NOT mock the Salesforce client directly.

- For DynamoDB tables: moto provides an empty AWS. Create tables in fixtures using
  `YourDyntasticModel.create_table()`; tables don't pre-exist in the moto environment.

- The only acceptable mock targets are time/randomness for determinism.

- Test names are contracts. test_classify_when_medical_record_then_returns_medical_type
  MUST assert the classification result equals the expected medical type. If the name
  promises a specific outcome, the assertion must verify that specific outcome.

- Include negative paths with realistic failure modes. Use specific exception types
  (DocumentNotFoundError, not Exception). Assert error context fields (document_id, stage).

- No assertion-free tests. Every test function must contain at least one assert statement
  that verifies a meaningful outcome.

- Do NOT add `pytest_plugins = ["mx2.testing.aws_fixtures"]` or similar; moto and
  responses are already enabled globally via the mx2-level conftest.
```

## Infrastructure Breadcrumbs

- moto autouse: enabled via `src/python/mx2/conftest.py` → `mx2.testing.aws`
- pytest-responses: global dev dependency
- FakeSalesforceManager: `mx2.testing.salesforce` (routes to `https://fake.salesforce.com`)
