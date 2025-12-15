"""
Custom exceptions for GBF tools.

Usage:
    from lib.utils.exceptions import ExtractionError, TranslationError
    
    raise ExtractionError("Failed to extract chapter", url=url, details={"status": 404})
"""
from typing import Optional, Dict, Any


class GBFToolError(Exception):
    """Base exception for all GBF tool errors."""
    
    def __init__(
        self, 
        message: str, 
        *,
        cause: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.cause = cause
        self.details = details or {}
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.details:
            parts.append(f"Details: {self.details}")
        if self.cause:
            parts.append(f"Caused by: {self.cause}")
        return " | ".join(parts)


class ExtractionError(GBFToolError):
    """Error during content extraction from wiki."""
    
    def __init__(
        self,
        message: str,
        *,
        url: Optional[str] = None,
        selector: Optional[str] = None,
        cause: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, cause=cause, details=details)
        self.url = url
        self.selector = selector
        if url:
            self.details["url"] = url
        if selector:
            self.details["selector"] = selector


class TranslationError(GBFToolError):
    """Error during translation."""
    
    def __init__(
        self,
        message: str,
        *,
        source_file: Optional[str] = None,
        api: Optional[str] = None,
        cause: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, cause=cause, details=details)
        self.source_file = source_file
        self.api = api
        if source_file:
            self.details["source_file"] = source_file
        if api:
            self.details["api"] = api


class NotionSyncError(GBFToolError):
    """Error during Notion synchronization."""
    
    def __init__(
        self,
        message: str,
        *,
        page_id: Optional[str] = None,
        operation: Optional[str] = None,
        cause: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, cause=cause, details=details)
        self.page_id = page_id
        self.operation = operation
        if page_id:
            self.details["page_id"] = page_id
        if operation:
            self.details["operation"] = operation


class ConfigError(GBFToolError):
    """Error in configuration."""
    
    def __init__(
        self,
        message: str,
        *,
        config_key: Optional[str] = None,
        expected_type: Optional[str] = None,
        cause: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, cause=cause, details=details)
        self.config_key = config_key
        self.expected_type = expected_type
        if config_key:
            self.details["config_key"] = config_key
        if expected_type:
            self.details["expected_type"] = expected_type


class APIError(GBFToolError):
    """Error from external API."""
    
    def __init__(
        self,
        message: str,
        *,
        api_name: str = "Unknown",
        status_code: Optional[int] = None,
        response: Optional[str] = None,
        cause: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, cause=cause, details=details)
        self.api_name = api_name
        self.status_code = status_code
        self.response = response
        self.details["api"] = api_name
        if status_code:
            self.details["status_code"] = status_code


class FileOperationError(GBFToolError):
    """Error during file operations."""
    
    def __init__(
        self,
        message: str,
        *,
        file_path: Optional[str] = None,
        operation: Optional[str] = None,  # read, write, delete, etc.
        cause: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, cause=cause, details=details)
        self.file_path = file_path
        self.operation = operation
        if file_path:
            self.details["file_path"] = file_path
        if operation:
            self.details["operation"] = operation

