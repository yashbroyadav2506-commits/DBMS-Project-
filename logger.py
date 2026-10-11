import sys
import logging

# Configure logger to output directly to stdout for serverless & cloud platforms
logger = logging.getLogger('grocery_app')
logger.setLevel(logging.INFO)

if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(name)s (%(module)s:%(lineno)d): %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
