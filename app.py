#!/usr/bin/env python3
"""
SSH GitHub Configurator
A desktop application to automate SSH key setup for GitHub

Main application entry point with improved error handling and modular design
"""

import tkinter as tk
import sys
import traceback
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from ui import SSHGitHubConfiguratorUI
from logger import app_logger
from utils import ErrorHandler


def setup_global_exception_handler():
    """Setup global exception handler to catch unhandled exceptions"""
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Allow Ctrl+C to work normally
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Log the exception
        app_logger.critical("Unhandled exception occurred", exc_info=(exc_type, exc_value, exc_traceback))
        
        # Show error to user
        error_msg = ErrorHandler.handle_exception(exc_value, "Global Exception Handler")
        
        try:
            import tkinter.messagebox as messagebox
            messagebox.showerror(
                "Critical Error", 
                f"An unexpected error occurred:\n\n{error_msg}\n\nThe application will continue running, but please check the logs."
            )
        except Exception:
            # If we can't show a message box, at least print to console
            print(f"CRITICAL ERROR: {error_msg}")
    
    sys.excepthook = handle_exception


def main():
    """Main function to run the application with comprehensive error handling"""
    try:
        # Setup global exception handling
        setup_global_exception_handler()
        
        app_logger.info("Starting SSH GitHub Configurator application")
        
        # Create main window with error handling
        root = tk.Tk()
        
        # Handle window close event
        def on_closing():
            try:
                app_logger.info("Application closing")
                root.quit()
                root.destroy()
            except Exception as e:
                app_logger.error(f"Error during application shutdown: {e}")
                sys.exit(1)
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Create application instance
        try:
            app = SSHGitHubConfiguratorUI(root)
            app._display_found_ssh_keys()
            app_logger.info("Application UI initialized successfully")
        except Exception as e:
            app_logger.critical(f"Failed to initialize application UI: {e}", exc_info=True)
            
            # Show error and exit gracefully
            import tkinter.messagebox as messagebox
            messagebox.showerror(
                "Initialization Error", 
                f"Failed to start the application:\n\n{ErrorHandler.handle_exception(e, 'Application Initialization')}\n\nPlease check the logs and try again."
            )
            return 1
        
        # Start the main loop
        try:
            app_logger.info("Starting main application loop")
            root.mainloop()
            app_logger.info("Application closed normally")
            return 0
            
        except Exception as e:
            app_logger.critical(f"Error in main loop: {e}", exc_info=True)
            return 1
            
    except Exception as e:
        # Last resort error handling
        try:
            app_logger.critical(f"Critical error in main function: {e}", exc_info=True)
        except Exception:
            print(f"CRITICAL: {e}")
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)