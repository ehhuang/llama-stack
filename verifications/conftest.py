def pytest_addoption(parser):
    parser.addoption(
        "--base-url",
        action="store",
        help="Base URL for OpenAI compatible API",
    )
    parser.addoption(
        "--api-key",
        action="store",
        help="API key",
    )
    parser.addoption(
        "--provider",
        action="store",
        help="Provider to use for testing",
    )


pytest_plugins = [
    "verifications.openai.fixtures.fixtures",
]
