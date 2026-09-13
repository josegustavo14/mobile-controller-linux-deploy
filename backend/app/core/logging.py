import logging


def configure_logging(level: str) -> None:
    """Use a concise, parseable format without request payloads or secrets."""
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
