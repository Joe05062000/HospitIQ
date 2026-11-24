"""Server-side deployment policy for the standalone public release."""


def private_demo() -> bool:
    """The published build has no private mode, including under environment overrides."""
    return False
