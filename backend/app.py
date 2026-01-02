"""
Flask REST API for Food Safety Analysis
Provides AI-powered food safety evaluation for the Replateo donation platform.
"""

import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from food_analyzer import analyze_food_image
from csv_storage import log_analysis

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure CORS for React frontend
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

# Maximum file size (10MB)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

# Allowed image extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename: str) -> bool:
    """Check if the file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_mime_type(filename: str) -> str:
    """Get MIME type from filename."""
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else "jpeg"
    mime_types = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp"
    }
    return mime_types.get(ext, "image/jpeg")


@app.route("/api/analyze-food", methods=["POST"])
def analyze_food():
    """
    Analyze a food image for safety and donation eligibility.
    
    Accepts: multipart/form-data with:
        - image: File (required) - The food image to analyze
        - preparationTime: string (required) - ISO datetime of food preparation
        - packageTime: string (required) - ISO datetime of food packaging
    
    Returns:
        JSON with classification, confidence, reasoning, and other analysis data
    """
    try:
        # Validate image file
        if "image" not in request.files:
            return jsonify({
                "error": "No image file provided",
                "classification": "NOT-EDIBLE",
                "confidence": 0.0,
                "reasoning": "Image is required for food safety analysis"
            }), 400
        
        image_file = request.files["image"]
        
        if image_file.filename == "":
            return jsonify({
                "error": "No image file selected",
                "classification": "NOT-EDIBLE",
                "confidence": 0.0,
                "reasoning": "A valid image file is required"
            }), 400
        
        if not allowed_file(image_file.filename):
            return jsonify({
                "error": "Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP",
                "classification": "NOT-EDIBLE",
                "confidence": 0.0,
                "reasoning": "Only image files are accepted for analysis"
            }), 400
        
        # Validate required form data
        preparation_time = request.form.get("preparationTime")
        package_time = request.form.get("packageTime")
        
        if not preparation_time:
            return jsonify({
                "error": "Preparation time is required",
                "classification": "NOT-EDIBLE",
                "confidence": 0.0,
                "reasoning": "Preparation time is needed for time-temperature analysis"
            }), 400
        
        if not package_time:
            return jsonify({
                "error": "Package time is required",
                "classification": "NOT-EDIBLE",
                "confidence": 0.0,
                "reasoning": "Package time is needed for time-temperature analysis"
            }), 400
        
        # Read image bytes
        image_bytes = image_file.read()
        mime_type = get_mime_type(image_file.filename)
        
        # Analyze the food image
        result = analyze_food_image(
            image_bytes=image_bytes,
            preparation_time=preparation_time,
            package_time=package_time,
            mime_type=mime_type
        )
        
        # Log the analysis for audit trail
        log_analysis(
            image_filename=image_file.filename,
            preparation_time=preparation_time,
            package_time=package_time,
            analysis_result=result
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        error_response = {
            "error": str(e),
            "classification": "NOT-EDIBLE",
            "confidence": 0.0,
            "reasoning": f"Analysis failed due to server error: {str(e)}"
        }
        return jsonify(error_response), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "food-safety-analyzer"
    }), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    
    print(f"Starting Food Safety Analysis API on port {port}")
    print(f"CORS enabled for: http://localhost:5173")
    
    app.run(host="0.0.0.0", port=port, debug=debug)
