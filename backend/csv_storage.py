"""
CSV Storage Module - Thread-safe CSV persistence for audit trail.
Stores all food analysis requests and results for compliance and debugging.
"""

import csv
import os
import threading
from datetime import datetime
from typing import Optional
import json

# Thread lock for file operations
_file_lock = threading.Lock()

# Data directory
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ANALYSIS_LOG_FILE = os.path.join(DATA_DIR, "food_analysis_log.csv")

# CSV headers
CSV_HEADERS = [
    "timestamp",
    "image_filename",
    "preparation_time",
    "package_time",
    "classification",
    "decision",
    "risk_level",
    "confidence",
    "reasoning_summary",
    "advisory",
    "error"
]


def _ensure_data_dir():
    """Create data directory if it doesn't exist."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def _ensure_csv_file():
    """Create CSV file with headers if it doesn't exist."""
    _ensure_data_dir()
    if not os.path.exists(ANALYSIS_LOG_FILE):
        with open(ANALYSIS_LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)


def log_analysis(
    image_filename: str,
    preparation_time: str,
    package_time: str,
    analysis_result: dict
) -> bool:
    """
    Log a food analysis result to the CSV file.
    
    Args:
        image_filename: Original filename of the uploaded image
        preparation_time: ISO format datetime string
        package_time: ISO format datetime string
        analysis_result: Dict containing the analysis result from food_analyzer
    
    Returns:
        bool: True if logging succeeded, False otherwise
    """
    try:
        with _file_lock:
            _ensure_csv_file()
            
            # Extract reasoning summary
            reasoning = analysis_result.get("reasoning", {})
            if isinstance(reasoning, dict):
                reasoning_summary = reasoning.get("final_assessment", str(reasoning))
            else:
                reasoning_summary = str(reasoning)
            
            # Truncate reasoning if too long
            if len(reasoning_summary) > 500:
                reasoning_summary = reasoning_summary[:497] + "..."
            
            row = [
                datetime.now().isoformat(),
                image_filename,
                preparation_time,
                package_time,
                analysis_result.get("classification", "UNKNOWN"),
                analysis_result.get("decision", "UNKNOWN"),
                analysis_result.get("risk_level", "UNKNOWN"),
                analysis_result.get("confidence", 0.0),
                reasoning_summary,
                analysis_result.get("advisory", ""),
                analysis_result.get("error", False)
            ]
            
            with open(ANALYSIS_LOG_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(row)
            
            return True
            
    except Exception as e:
        print(f"Error logging analysis: {e}")
        return False


def get_analysis_history(limit: int = 100) -> list:
    """
    Retrieve recent analysis history.
    
    Args:
        limit: Maximum number of records to return
    
    Returns:
        List of dicts containing analysis records
    """
    try:
        with _file_lock:
            if not os.path.exists(ANALYSIS_LOG_FILE):
                return []
            
            with open(ANALYSIS_LOG_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            # Return most recent records
            return rows[-limit:] if len(rows) > limit else rows
            
    except Exception as e:
        print(f"Error reading analysis history: {e}")
        return []


def get_statistics() -> dict:
    """
    Get statistics about food analysis results.
    
    Returns:
        Dict containing analysis statistics
    """
    try:
        history = get_analysis_history(limit=10000)
        
        if not history:
            return {
                "total_analyses": 0,
                "edible_count": 0,
                "not_edible_count": 0,
                "error_count": 0,
                "edible_rate": 0.0
            }
        
        total = len(history)
        edible = sum(1 for r in history if r.get("classification") == "EDIBLE")
        not_edible = sum(1 for r in history if r.get("classification") == "NOT-EDIBLE")
        errors = sum(1 for r in history if r.get("error") == "True")
        
        return {
            "total_analyses": total,
            "edible_count": edible,
            "not_edible_count": not_edible,
            "error_count": errors,
            "edible_rate": round(edible / total * 100, 2) if total > 0 else 0.0
        }
        
    except Exception as e:
        print(f"Error calculating statistics: {e}")
        return {
            "total_analyses": 0,
            "edible_count": 0,
            "not_edible_count": 0,
            "error_count": 0,
            "edible_rate": 0.0,
            "error": str(e)
        }
