"""Console utilities for better output formatting and management."""

import sys
import os
from typing import Optional


class ConsoleManager:
    """Manages console output for cleaner real-time monitoring displays."""
    
    def __init__(self):
        """Initialize console manager."""
        self.last_status_line = ""
        self.supports_ansi = self._supports_ansi_colors()
    
    def _supports_ansi_colors(self) -> bool:
        """Check if terminal supports ANSI escape codes."""
        # Check if we're in a terminal that supports ANSI
        if not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
            return False
        
        # Windows CMD doesn't support ANSI by default, but Windows Terminal does
        if sys.platform == "win32":
            return os.environ.get('TERM') is not None or 'WT_SESSION' in os.environ
        
        return True
    
    def clear_line(self):
        """Clear the current line."""
        if self.supports_ansi:
            print('\r\033[K', end='', flush=True)
        else:
            # Fallback: print spaces to clear the line
            print('\r' + ' ' * 80 + '\r', end='', flush=True)
    
    def print_status(self, message: str, temporary: bool = False):
        """Print a status message, optionally temporary (will be overwritten).
        
        Args:
            message: The message to print
            temporary: If True, this line can be overwritten by the next status
        """
        # Clear any previous temporary status
        if self.last_status_line and temporary:
            self.clear_line()
        
        if temporary:
            print(message, end='', flush=True)
            self.last_status_line = message
        else:
            # For permanent messages, first clear any temporary status
            if self.last_status_line:
                self.clear_line()
                self.last_status_line = ""
            print(message, flush=True)
    
    def print_permanent(self, message: str):
        """Print a permanent message (will not be overwritten)."""
        self.print_status(message, temporary=False)
    
    def print_temporary(self, message: str):
        """Print a temporary status message (can be overwritten)."""
        self.print_status(message, temporary=True)
    
    def update_status_if_needed(self, message: str):
        """Update the status line only if the message has changed."""
        if self.last_status_line != message:
            self.print_temporary(message)
    
    def print_inline_result(self, start_message: str, result_message: str):
        """Print a message with an inline result (e.g., 'Processing... ✅').
        
        Args:
            start_message: The initial message (e.g., 'Processing...')
            result_message: The result to append (e.g., '✅' or '❌ Error')
        """
        # Clear any temporary status first
        if self.last_status_line:
            self.clear_line()
            self.last_status_line = ""
        
        print(f"{start_message} {result_message}", flush=True)
    
    def newline(self):
        """Print a newline, clearing any temporary status first."""
        if self.last_status_line:
            self.clear_line()
            self.last_status_line = ""
        print()


# Global console manager instance
console = ConsoleManager()