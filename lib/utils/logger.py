"""
Unified logging system for GBF tools.

Usage:
    from lib.utils.logger import get_logger, setup_logging
    
    # Basic usage
    logger = get_logger(__name__)
    logger.info("Starting extraction...")
    logger.error("Failed to extract", exc_info=True)
    
    # Setup with options
    setup_logging(level="DEBUG", log_file="output.log")
"""
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Color codes for terminal output
COLORS = {
    'DEBUG': '\033[36m',     # Cyan
    'INFO': '\033[32m',      # Green
    'WARNING': '\033[33m',   # Yellow
    'ERROR': '\033[31m',     # Red
    'CRITICAL': '\033[35m',  # Magenta
    'RESET': '\033[0m',
    'BOLD': '\033[1m',
    'DIM': '\033[2m',
}

# Check if terminal supports colors
SUPPORTS_COLOR = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


class ColoredFormatter(logging.Formatter):
    """Formatter with colored output for terminal."""
    
    def __init__(self, use_color: bool = True):
        super().__init__()
        self.use_color = use_color and SUPPORTS_COLOR
    
    def format(self, record: logging.LogRecord) -> str:
        if self.use_color:
            color = COLORS.get(record.levelname, COLORS['RESET'])
            reset = COLORS['RESET']
            dim = COLORS['DIM']
        else:
            color = reset = dim = ""
        
        # Shorten module name
        name = record.name
        if name.startswith('lib.'):
            name = name[4:]
        
        # Timestamp (dimmed)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Format: HH:MM:SS [LEVEL] module: message
        formatted = f"{dim}{timestamp}{reset} {color}[{record.levelname:7}]{reset} {name}: {record.getMessage()}"
        
        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted


class FileFormatter(logging.Formatter):
    """Formatter for file output (no colors, full timestamps)."""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s [%(levelname)-7s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


class JSONFormatter(logging.Formatter):
    """Formatter for JSON output (useful for log aggregation)."""
    
    def format(self, record: logging.LogRecord) -> str:
        import json
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data, ensure_ascii=False)


# Global state
_loggers: dict = {}
_configured = False
_log_level = logging.INFO


def setup_logging(
    level: LogLevel = "INFO",
    log_file: Optional[str] = None,
    json_format: bool = False,
    quiet: bool = False
) -> None:
    """
    Setup logging for the entire application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        json_format: Use JSON format for file output
        quiet: Suppress console output
    
    Example:
        >>> setup_logging(level="DEBUG", log_file="app.log")
    """
    global _configured, _log_level
    
    _log_level = getattr(logging, level.upper())
    
    root = logging.getLogger('lib')
    root.setLevel(_log_level)
    root.handlers.clear()
    
    # Console handler (unless quiet)
    if not quiet:
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(_log_level)
        console.setFormatter(ColoredFormatter())
        root.addHandler(console)
    
    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # Always debug for file
        
        if json_format:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(FileFormatter())
        
        root.addHandler(file_handler)
    
    _configured = True


def configure_root_logger(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    verbose: bool = False
) -> None:
    """Legacy function for backward compatibility."""
    log_level = "DEBUG" if verbose else "INFO"
    if level == logging.DEBUG:
        log_level = "DEBUG"
    elif level == logging.WARNING:
        log_level = "WARNING"
    elif level == logging.ERROR:
        log_level = "ERROR"
    
    setup_logging(level=log_level, log_file=str(log_file) if log_file else None)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing started")
    """
    global _configured
    
    # Auto-configure if needed
    if not _configured:
        setup_logging()
    
    # Normalize name to 'lib' namespace
    if not name.startswith('lib'):
        if name.startswith('__'):
            name = 'lib'
        else:
            name = f'lib.{name}'
    
    # Cache and return
    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)
    
    return _loggers[name]


def set_level(level: LogLevel) -> None:
    """Change log level at runtime."""
    global _log_level
    _log_level = getattr(logging, level.upper())
    logging.getLogger('lib').setLevel(_log_level)


# Convenience functions
def debug(msg: str, *args, **kwargs) -> None:
    """Log debug message."""
    get_logger('lib').debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs) -> None:
    """Log info message."""
    get_logger('lib').info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs) -> None:
    """Log warning message."""
    get_logger('lib').warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs) -> None:
    """Log error message."""
    get_logger('lib').error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs) -> None:
    """Log critical message."""
    get_logger('lib').critical(msg, *args, **kwargs)


# Context manager for temporary log level
class log_level_context:
    """Temporarily change log level."""
    
    def __init__(self, level: LogLevel):
        self.level = level
        self.old_level = None
    
    def __enter__(self):
        self.old_level = _log_level
        set_level(self.level)
        return self
    
    def __exit__(self, *args):
        if self.old_level:
            logging.getLogger('lib').setLevel(self.old_level)

