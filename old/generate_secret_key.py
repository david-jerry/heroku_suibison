import secrets

from src.utils.logger import LOGGER

if __name__ == "__main__":
    LOGGER.info(secrets.token_hex(32))
    