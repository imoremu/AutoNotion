# Shared module for dual deployment
import logging
import logging.config
import os
import sys

def setup_universal_logging():
    """
    Sets up universal logging (DEBUG to console) for all environments.
    Automatically executed when the 'shared' package is imported.
    """
       
    log_level = os.environ.get('SERVICE_LOG_LEVEL', 'DEBUG').upper()
    
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s %(levelname)s [%(name)s:%(lineno)d] %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "detailed",
                "stream": "ext://sys.stdout"  # 'stdout' is universal
            }
        },
        "root": {
            "level": log_level,
            "handlers": ["console"]
        }
    }
    
    try:
        logging.config.dictConfig(config)
        print(f"Universal logging configured. Level: {log_level}")
    except Exception as e:    
        print(f"Error configuring logging with dictConfig: {e}. Using basicConfig.")
        logging.basicConfig(level=log_level, stream=sys.stdout, format='%(asctime)s %(levelname)s [%(name)s] %(message)s')

setup_universal_logging()
