import logging
from rich.console import Console
from rich.logging import RichHandler

console = Console()

def setup_logger():
    logging.basicConfig(
        level="INFO",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)]
    )
    return logging.getLogger("ghost")

logger = setup_logger()