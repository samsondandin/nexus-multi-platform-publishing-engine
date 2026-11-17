# Contributing to NEXUS

Thank you for your interest in contributing to the NEXUS Multi-Platform Publishing Engine!

## Development Workflow

1. **Fork or branch**:
   Create a descriptive branch for your work:
   ```bash
   git checkout -b feat/add-threads-platform
   ```

2. **Set up local environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Code Style & Quality**:
   - Ensure code follows clean Python standards.
   - Run `ruff check .` and fix any linting issues.
   - Run `pytest` to ensure all tests pass.

4. **Adding a New Platform Adapter**:
   - Subclass `BasePlatformAdapter` from `app.platforms.base`.
   - Implement `platform_name`, `public_access_supported`, `docs_url`, `description`, `is_configured()`, and `publish()`.
   - Never raise unhandled exceptions from `publish()`; use `create_failed_result()` or `create_success_result()`.
   - Add unit tests in `tests/test_platforms.py` with mocked HTTP responses.
   - Register the adapter in `app/services/posting_service.py`.

5. **Commit Standards**:
   - Use conventional commit messages: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.
