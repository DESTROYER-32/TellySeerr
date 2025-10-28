import importlib
import pkgutil
import logging

logger = logging.getLogger(__name__)


def load_all_handlers(app):
    """Auto-import all modules in this package to register their handlers."""
    package_name = __name__
    package_path = __path__
    logger.info(f"Loading handlers from package: {package_name}")

    for _, module_name, _ in pkgutil.iter_modules(package_path):
        if module_name == "__init__":
            continue

        try:
            importlib.import_module(f".{module_name}", package_name)
            logger.info(f"Successfully loaded handler module: {module_name}")
        except Exception as e:
            logger.error(f"Failed to load handler {module_name}: {e}")
