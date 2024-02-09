import logging


app_logger = logging.getLogger("app")
app_logger.setLevel(logging.INFO)

log_handler = logging.StreamHandler()
log_formatter = logging.Formatter("%(name)s - %(asctime)s - %(levelname)s: %(message)s")

log_handler.setFormatter(log_formatter)
app_logger.addHandler(log_handler)