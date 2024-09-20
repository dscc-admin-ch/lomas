import logging
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s --- %(levelname)s - "
                "[%(filename)s:%(lineno)s - %(funcName)s()] - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
            "level": "INFO",
        },
        "file": {
            "class": "logging.FileHandler",
            "formatter": "standard",
            "filename": "lomas_app.log",
            "level": "INFO",
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"],
        "propagate": True,
    },
}
logging.config.dictConfig(LOGGING_CONFIG)

LOG = logging.getLogger("")
