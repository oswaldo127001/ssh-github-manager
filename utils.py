#!/usr/bin/env python3
"""
Utilities module for SSH GitHub Configurator
Contains common functions, decorators, and helper classes
"""

import functools
import traceback
from typing import Callable, Any
from logger import app_logger


def safe_execute(show_error: bool = True, default_return: Any = None):
    """
    Decorator to safely execute functions with comprehensive error handling
    
    Args:
        show_error: Whether to show error dialog to user
        default_return: Value to return on error
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                app_logger.debug(f"Executing function: {func.__name__}")
                result = func(*args, **kwargs)
                app_logger.debug(f"Function {func.__name__} completed successfully")
                return result
            except Exception as e:
                app_logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                
                if show_error and hasattr(args[0], 'show_error_message'):
                    # If it's a method call and the object has show_error_message method
                    args[0].show_error_message(f"Error in {func.__name__}", str(e))
                
                return default_return
        return wrapper
    return decorator


def validate_input(validation_func: Callable, error_message: str):
    """
    Decorator to validate function inputs
    
    Args:
        validation_func: Function that returns True if input is valid
        error_message: Error message to show if validation fails
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                if not validation_func(*args, **kwargs):
                    raise ValueError(error_message)
                return func(*args, **kwargs)
            except Exception as e:
                app_logger.error(f"Validation error in {func.__name__}: {e}")
                raise
        return wrapper
    return decorator


class ErrorHandler:
    """Centralized error handling class"""
    
    @staticmethod
    def handle_exception(exception: Exception, context: str = "") -> str:
        """
        Handle exceptions and return user-friendly error messages
        
        Args:
            exception: The exception to handle
            context: Additional context about where the error occurred
            
        Returns:
            User-friendly error message
        """
        app_logger.error(f"Exception in {context}: {exception}", exc_info=True)
        
        # Map common exceptions to user-friendly messages
        error_messages = {
            FileNotFoundError: "Required file not found. Please check your installation.",
            PermissionError: "Permission denied. Please check file permissions or run as administrator.",
            ConnectionError: "Network connection error. Please check your internet connection.",
            TimeoutError: "Operation timed out. Please try again.",
            ValueError: "Invalid input provided. Please check your data.",
            OSError: "System error occurred. Please check your system configuration."
        }
        
        exception_type = type(exception)
        if exception_type in error_messages:
            return f"{error_messages[exception_type]}\n\nTechnical details: {str(exception)}"
        else:
            return f"An unexpected error occurred: {str(exception)}"
    
    @staticmethod
    def log_system_info():
        """Log system information for debugging"""
        import platform
        import sys
        
        info = {
            "Platform": platform.platform(),
            "System": platform.system(),
            "Python Version": sys.version,
            "Architecture": platform.architecture()[0]
        }
        
        app_logger.info("System Information:")
        for key, value in info.items():
            app_logger.info(f"  {key}: {value}")


class ClipboardManager:
    """Cross-platform clipboard management"""
    
    @staticmethod
    def copy_to_clipboard(text: str, root_widget=None) -> bool:
        """
        Copy text to clipboard with fallback methods
        
        Args:
            text: Text to copy
            root_widget: Tkinter root widget (if available)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Try tkinter clipboard first (if root widget available)
            if root_widget:
                try:
                    root_widget.clipboard_clear()
                    root_widget.clipboard_append(text)
                    root_widget.update()  # Ensure clipboard is updated
                    app_logger.info("Text copied to clipboard using tkinter")
                    return True
                except Exception as e:
                    app_logger.warning(f"Tkinter clipboard failed: {e}")
            
            # Fallback to system-specific methods
            import platform
            system = platform.system()
            
            if system == "Windows":
                return ClipboardManager._copy_windows(text)
            elif system == "Darwin":  # macOS
                return ClipboardManager._copy_macos(text)
            elif system == "Linux":
                return ClipboardManager._copy_linux(text)
            else:
                app_logger.error(f"Unsupported platform for clipboard: {system}")
                return False
                
        except Exception as e:
            app_logger.error(f"Clipboard operation failed: {e}", exc_info=True)
            return False
    
    @staticmethod
    def _copy_windows(text: str) -> bool:
        """Copy to clipboard on Windows"""
        try:
            import subprocess
            process = subprocess.Popen(['clip'], stdin=subprocess.PIPE, text=True)
            process.communicate(input=text)
            app_logger.info("Text copied to clipboard using Windows clip")
            return process.returncode == 0
        except Exception as e:
            app_logger.error(f"Windows clipboard copy failed: {e}")
            return False
    
    @staticmethod
    def _copy_macos(text: str) -> bool:
        """Copy to clipboard on macOS"""
        try:
            import subprocess
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE, text=True)
            process.communicate(input=text)
            app_logger.info("Text copied to clipboard using macOS pbcopy")
            return process.returncode == 0
        except Exception as e:
            app_logger.error(f"macOS clipboard copy failed: {e}")
            return False
    
    @staticmethod
    def _copy_linux(text: str) -> bool:
        """Copy to clipboard on Linux"""
        try:
            import subprocess
            
            # Try xclip first
            try:
                process = subprocess.Popen(['xclip', '-selection', 'clipboard'], 
                                        stdin=subprocess.PIPE, text=True)
                process.communicate(input=text)
                if process.returncode == 0:
                    app_logger.info("Text copied to clipboard using xclip")
                    return True
            except FileNotFoundError:
                pass
            
            # Try xsel as fallback
            try:
                process = subprocess.Popen(['xsel', '--clipboard', '--input'], 
                                        stdin=subprocess.PIPE, text=True)
                process.communicate(input=text)
                if process.returncode == 0:
                    app_logger.info("Text copied to clipboard using xsel")
                    return True
            except FileNotFoundError:
                pass
            
            app_logger.error("No clipboard utility found (xclip or xsel)")
            return False
            
        except Exception as e:
            app_logger.error(f"Linux clipboard copy failed: {e}")
            return False


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."