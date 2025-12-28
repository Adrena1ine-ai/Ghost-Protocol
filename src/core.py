import logging
from rich.console import Console
from rich.logging import RichHandler
from .utils import GhostLogHandler

console = Console()

def setup_logger():
    ghost_handler = GhostLogHandler()
    
    logging.basicConfig(
        level="INFO",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            ghost_handler,
            RichHandler(rich_tracebacks=True, show_path=False)
        ]
    )
    return logging.getLogger("ghost")

logger = setup_logger()