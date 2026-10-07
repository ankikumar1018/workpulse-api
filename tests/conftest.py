"""Shared pytest configuration."""


def pytest_addoption(parser):
    parser.addoption(
        "--whatsapp-test-db-url",
        default=None,
        help="Disposable migrated PostgreSQL URL; database name must start with workpulse_test",
    )
