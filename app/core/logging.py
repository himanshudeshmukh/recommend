from __future__ import annotations
 
"""Central logging setup for the service.
 
 ╔══════════════════════════════════════════════════════════════════════════════╗
 ║                        LOGGING CONFIGURATION                                ║
 ║                                                                              ║
 ║  This module configures a single, consistent logging format for the entire   ║
 ║  application. Every log message from every module will follow this format:   ║
 ║                                                                              ║
 ║    2026-05-12 10:30:45 | INFO | app.api.routes | 🔍 NEW REQUEST: ...        ║
 ║                                                                              ║
 ║  The format includes:                                                        ║
 ║    • Timestamp — when the event happened                                     ║
 ║    • Level    — INFO, WARNING, ERROR, or DEBUG                               ║
 ║    • Module   — which Python file produced the message                       ║
 ║    • Message  — a human-readable description of what happened                ║
 ╚══════════════════════════════════════════════════════════════════════════════╝
 """
 
 # Import the standard logging package so we can configure application logs.
import logging
 
 
def configure_logging() -> None:
    """Configure logging with a readable production-friendly format.
 
     This function should be called exactly ONCE at application startup,
     Before any other module writes log messages. It sets the global
     Log level to INFO and applies a uniform timestamp + module format.
     """
 
    logging.basicConfig(
         level=logging.INFO,
         format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
         datefmt="%Y-%m-%d %H:%M:%S",
     )