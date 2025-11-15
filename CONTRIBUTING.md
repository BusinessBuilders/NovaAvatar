# Contributing to NovaAvatar

Thank you for your interest in contributing to NovaAvatar! This document provides guidelines and instructions for contributing.

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/BusinessBuilders/NovaAvatar.git
cd NovaAvatar
```

### 2. Create Virtual Environment

```bash
python -m venv omniavatar_env
source omniavatar_env/bin/activate  # Linux/Mac
# omniavatar_env\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
# Production dependencies
pip install -r requirements.txt

# Development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### 4. Set Up Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

## Development Workflow

### Code Quality

We use several tools to maintain code quality:

- **Black** - Code formatting
- **Ruff** - Fast linting
- **isort** - Import sorting
- **mypy** - Type checking
- **pytest** - Testing

### Running Code Quality Checks

```bash
# Format code
black services/ api/ frontend/ config/

# Lint code
ruff check services/ api/ frontend/ config/ --fix

# Sort imports
isort services/ api/ frontend/ config/

# Type check
mypy services/ api/ frontend/ config/

# Run all checks
pre-commit run --all-files
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=services --cov=api --cov=frontend --cov-report=html

# Run specific test file
pytest tests/unit/services/test_orchestrator.py

# Run specific test
pytest tests/unit/services/test_orchestrator.py::TestPipelineOrchestrator::test_scrape_content

# Run unit tests only
pytest -m unit

# Run integration tests only
pytest -m integration
```

### Writing Tests

All new features should include tests. Follow these guidelines:

1. **Unit Tests**: Test individual functions/methods in isolation
2. **Integration Tests**: Test multiple components working together
3. **Use Fixtures**: Leverage pytest fixtures for test data
4. **Mock External Services**: Use mocks for API calls
5. **Coverage**: Aim for >80% code coverage

Example test:

```python
@pytest.mark.unit
async def test_my_feature(orchestrator, sample_content_item):
    """Test description."""
    # Arrange
    orchestrator.service.method = AsyncMock(return_value=expected)

    # Act
    result = await orchestrator.my_feature(sample_content_item)

    # Assert
    assert result == expected
```

## Pull Request Process

### 1. Create a Feature Branch

```bash
git checkout -b feature/my-new-feature
```

### 2. Make Your Changes

- Write clear, descriptive commit messages
- Follow the existing code style
- Add tests for new features
- Update documentation as needed

### 3. Run Tests and Checks

```bash
# Run all checks
pre-commit run --all-files

# Run tests
pytest

# Ensure tests pass and coverage is maintained
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "Add feature: description of changes"
```

Good commit messages:
- `feat: Add video batch processing endpoint`
- `fix: Correct VRAM management in avatar service`
- `docs: Update API documentation`
- `test: Add unit tests for content scraper`
- `refactor: Simplify orchestrator pipeline logic`

### 5. Push and Create PR

```bash
git push origin feature/my-new-feature
```

Then create a Pull Request on GitHub with:
- Clear description of changes
- Reference to related issues
- Screenshots/demos if applicable
- Test results

## Code Style Guidelines

### Python Style

- Follow PEP 8
- Use type hints where appropriate
- Write docstrings for all public functions/classes
- Keep functions focused and small (<50 lines)
- Use meaningful variable names

### Docstring Format

Use Google-style docstrings:

```python
def my_function(param1: str, param2: int) -> bool:
    """
    Brief description of function.

    Longer description if needed, explaining behavior,
    edge cases, etc.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: Description of when this is raised

    Example:
        >>> my_function("test", 42)
        True
    """
    pass
```

### Import Order

1. Standard library imports
2. Third-party imports
3. Local application imports

Sorted alphabetically within each group.

## Architecture Guidelines

### Adding New Services

1. Create service class in `services/`
2. Add Pydantic models for inputs/outputs
3. Implement async methods where appropriate
4. Add comprehensive error handling
5. Write unit tests
6. Update orchestrator if needed
7. Document in ARCHITECTURE.md

### Adding API Endpoints

1. Add endpoint to `api/server.py`
2. Use FastAPI best practices
3. Add request/response models
4. Include error responses
5. Add endpoint tests
6. Update API documentation

## Testing External APIs

When testing code that uses external APIs:

1. **Mock API calls** - Never make real API calls in tests
2. **Use fixtures** - Create sample responses
3. **Test error cases** - Mock failures and timeouts
4. **Skip if needed** - Mark tests requiring API keys:

```python
@pytest.mark.requires_api_keys
def test_openai_integration():
    pass
```

## Documentation

Update documentation when:
- Adding new features
- Changing behavior
- Modifying configuration options
- Adding dependencies

Files to update:
- `README.md` - High-level overview
- `SETUP.md` - Installation/setup instructions
- `ARCHITECTURE.md` - System architecture
- Inline docstrings - Code documentation

## Questions or Issues?

- Open an issue on GitHub
- Join our community discussions
- Check existing issues/PRs first

Thank you for contributing to NovaAvatar!
