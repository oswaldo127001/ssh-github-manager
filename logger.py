#!/usr/bin/env python3
"""
Logging module for SSH GitHub Configurator
Provides centralized logging functionality for debugging and error tracking
"""

import logging
import os
from pathlib import Path
from datetime import datetime


class AppLogger:
    """Centralized logging class for the application"""
    
    def __init__(self, log_level=logging.INFO):
        self.logger = logging.getLogger("SSHGitHubConfigurator")
        self.logger.setLevel(log_level)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup logging handlers for file and console output"""
        # Create logs directory if it doesn't exist
        log_dir = Path.home() / ".ssh_github_configurator_logs"
        log_dir.mkdir(exist_ok=True)
        
        # File handler
        log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def debug(self, message):
        """Log debug message"""
        self.logger.debug(message)
    
    def info(self, message):
        """Log info message"""
        self.logger.info(message)
    
    def warning(self, message):
        """Log warning message"""
        self.logger.warning(message)
    
    def error(self, message, exc_info=False):
        """Log error message"""
        self.logger.error(message, exc_info=exc_info)
    
    def critical(self, message, exc_info=False):
        """Log critical message"""
        self.logger.critical(message, exc_info=exc_info)


# Global logger instance
app_logger = AppLogger()