import os
from src.shared.common_fn import get_value_from_env

try:
    from google.cloud import logging as gclogger
    GCP_LOGGING_AVAILABLE = True
except ImportError:
    GCP_LOGGING_AVAILABLE = False

class CustomLogger:
    def __init__(self):
        self.is_gcp_log_enabled = get_value_from_env("GCP_LOG_METRICS_ENABLED", "False", "bool")
        if self.is_gcp_log_enabled and GCP_LOGGING_AVAILABLE:
            self.logging_client = gclogger.Client()
            self.logger_name = "llm_experiments_metrics"
            self.logger = self.logging_client.logger(self.logger_name)
        else:
            self.logger = None

    def log_struct(self, message, severity="DEFAULT"):
        if self.is_gcp_log_enabled and GCP_LOGGING_AVAILABLE and self.logger is not None:
            self.logger.log_struct({"message": message, "severity": severity})
        else:
            print(f"[{severity}]{message}")
