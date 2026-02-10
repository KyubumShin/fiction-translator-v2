"""Fiction Translator Sidecar - Entry Point"""
import asyncio
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,  # Log to stderr, stdout is for IPC
)

logger = logging.getLogger(__name__)


def main():
    """Entry point for the sidecar process."""
    logger.info("Fiction Translator sidecar starting...")

    from fiction_translator.db.session import init_db
    from fiction_translator.ipc.server import JsonRpcServer

    # Initialize database
    init_db()

    # Start IPC server
    server = JsonRpcServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
