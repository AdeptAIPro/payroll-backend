import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional

class StructuredLogger:
    """Structured logging utility for the payroll system"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup logger with proper formatting"""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _format_log_entry(self, level: str, message: str, **kwargs) -> str:
        """Format log entry as JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.upper(),
            "message": message,
            **kwargs
        }
        return json.dumps(log_entry)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        log_entry = self._format_log_entry("INFO", message, **kwargs)
        self.logger.info(log_entry)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        log_entry = self._format_log_entry("ERROR", message, **kwargs)
        self.logger.error(log_entry)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        log_entry = self._format_log_entry("WARNING", message, **kwargs)
        self.logger.warning(log_entry)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        log_entry = self._format_log_entry("DEBUG", message, **kwargs)
        self.logger.debug(log_entry)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        log_entry = self._format_log_entry("CRITICAL", message, **kwargs)
        self.logger.critical(log_entry)

# Global logger instances
auth_logger = StructuredLogger("auth")
employee_logger = StructuredLogger("employee")
timesheet_logger = StructuredLogger("timesheet")
payroll_logger = StructuredLogger("payroll")
api_logger = StructuredLogger("api") 