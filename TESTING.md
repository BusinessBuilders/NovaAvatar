# Testing Guide for NovaAvatar

This document explains how to run and write tests for NovaAvatar.

## Quick Start

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test markers
pytest -m unit          # Only unit tests
pytest -m integration   # Only integration tests
pytest -m "not slow"    # Skip slow tests
```

## Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── unit/                 # Unit tests
│   ├── services/
│   │   ├── test_content_scraper.py
│   │   ├── test_script_generator.py
│   │   ├── test_image_generator.py
│   │   ├── test_tts_service.py
│   │   ├── test_avatar_service.py
│   │   └── test_orchestrator.py
│   ├── api/
│   │   └── test_server.py
│   └── frontend/
│       └── test_app.py
├── integration/          # Integration tests
│   ├── test_full_pipeline.py
│   └── test_api_endpoints.py
└── fixtures/             # Test data files
    ├── sample_audio.wav
    ├── sample_image.jpg
    └── sample_content.json
```

## Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Tests multiple components
- `@pytest.mark.slow` - Long-running tests (>5s)
- `@pytest.mark.requires_api_keys` - Needs API keys to run
- `@pytest.mark.requires_gpu` - Needs GPU to run

### Running Specific Markers

```bash
# Run only unit tests (fast)
pytest -m unit

# Run all except slow tests
pytest -m "not slow"

# Run integration tests only
pytest -m integration

# Skip tests requiring API keys
pytest -m "not requires_api_keys"
```

## Available Fixtures

Common fixtures available in all tests (from `conftest.py`):

### Data Fixtures

- `fake` - Faker instance for generating test data
- `temp_dir` - Temporary directory (auto-cleaned)
- `sample_content_item` - ContentItem example
- `sample_video_script` - VideoScript example
- `mock_storage_dir` - Mock storage directory structure

### Mock Fixtures

- `mock_openai_client` - Mocked OpenAI client
- `mock_replicate_client` - Mocked Replicate client
- `mock_avatar_service` - Mocked AvatarService

### Usage Example

```python
@pytest.mark.unit
async def test_my_feature(fake, temp_dir, sample_content_item):
    """Test using fixtures."""
    # fake provides fake data
    title = fake.sentence()

    # temp_dir provides temporary directory
    output_file = temp_dir / "output.txt"

    # sample_content_item provides test data
    assert sample_content_item.title
```

## Writing Tests

### Unit Test Example

```python
@pytest.mark.unit
async def test_scrape_content(orchestrator, sample_content_item):
    """Test content scraping."""
    # Mock the scraper
    orchestrator.content_scraper.scrape_all = AsyncMock(
        return_value=[sample_content_item]
    )

    # Call the method
    items = await orchestrator.scrape_content(max_items=5)

    # Assert results
    assert len(items) == 1
    assert items[0].title == sample_content_item.title
```

### Integration Test Example

```python
@pytest.mark.integration
@pytest.mark.slow
async def test_full_pipeline_e2e(orchestrator):
    """Test full end-to-end pipeline."""
    # This test actually calls multiple services
    content = ContentItem(
        title="Test Article",
        description="Test description",
        url="https://example.com/article",
        source_name="Test",
    )

    job = await orchestrator.create_video_from_content(content)

    assert job.status in [JobStatus.COMPLETED, JobStatus.QUEUED_FOR_REVIEW]
    assert job.video_file is not None
```

### Testing Async Code

Use `@pytest.mark.asyncio` for async tests:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result is not None
```

### Mocking External APIs

Always mock external API calls:

```python
@pytest.mark.unit
async def test_with_api_mock():
    with patch('openai.ChatCompletion.create') as mock_create:
        mock_create.return_value = {"choices": [{"message": {"content": "test"}}]}

        result = await generate_script(...)

        assert mock_create.called
        assert result is not None
```

## Coverage

### Running Coverage

```bash
# Generate coverage report
pytest --cov=services --cov=api --cov=frontend

# Generate HTML report
pytest --cov --cov-report=html
open htmlcov/index.html

# Generate XML report (for CI)
pytest --cov --cov-report=xml
```

### Coverage Goals

- **Overall**: >70%
- **Core Services**: >80%
- **API Endpoints**: >80%
- **Critical Paths**: >90%

### Excluding from Coverage

Mark code that shouldn't be covered:

```python
def debug_only_function():
    """This function is only for debugging."""
    ...  # pragma: no cover
```

## Continuous Integration

Tests run automatically on:
- Push to `main` or `develop`
- Pull requests
- Weekly schedule (security scans)

### GitHub Actions Workflows

- `.github/workflows/test.yml` - Run tests
- `.github/workflows/lint.yml` - Code quality checks
- `.github/workflows/security.yml` - Security scans

### CI Requirements

Pull requests must:
- ✅ Pass all tests
- ✅ Pass linting checks
- ✅ Maintain >70% coverage
- ✅ Pass security scans

## Debugging Tests

### Running in Verbose Mode

```bash
# Show detailed output
pytest -v

# Show print statements
pytest -s

# Show local variables on failure
pytest -l

# Drop into debugger on failure
pytest --pdb
```

### Using IPython Debugger

```python
def test_something():
    import ipdb; ipdb.set_trace()  # Breakpoint
    result = my_function()
    assert result
```

### Debugging Specific Test

```bash
# Run single test with debugger
pytest tests/unit/services/test_orchestrator.py::test_scrape_content --pdb
```

## Performance Testing

### Marking Slow Tests

```python
@pytest.mark.slow
def test_large_batch_processing():
    """This test takes >5 seconds."""
    ...
```

### Timing Tests

```bash
# Show slowest 10 tests
pytest --durations=10
```

### Timeout Tests

```python
@pytest.mark.timeout(30)  # Fail if takes >30s
def test_with_timeout():
    ...
```

## Common Testing Patterns

### Testing Exceptions

```python
def test_invalid_input():
    with pytest.raises(ValueError) as exc_info:
        my_function(invalid_input)

    assert "expected error message" in str(exc_info.value)
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("test1", "result1"),
    ("test2", "result2"),
    ("test3", "result3"),
])
def test_multiple_cases(input, expected):
    assert my_function(input) == expected
```

### Testing Files

```python
def test_file_creation(temp_dir):
    output_file = temp_dir / "test.txt"

    create_file(output_file)

    assert output_file.exists()
    assert output_file.read_text() == "expected content"
```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Clear Names**: Test names should describe what's being tested
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Mock External**: Never call real APIs in tests
5. **Fast Tests**: Unit tests should run in <1s each
6. **Test Edge Cases**: Don't just test happy paths
7. **Use Fixtures**: Reuse test data and setup
8. **Document Tests**: Add docstrings explaining complex tests

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
