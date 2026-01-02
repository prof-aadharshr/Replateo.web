"""
Food Analyzer Module - Google Gemini 2.5 Flash Integration
Provides AI-powered food safety analysis for donation decisions.
"""

import os
import json
import base64
import re
from datetime import datetime
from typing import Optional

import google.generativeai as genai
from dotenv import load_dotenv

from system_prompt import get_system_prompt

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY environment variable is not set")

genai.configure(api_key=GEMINI_API_KEY)

# Initialize the model
MODEL_NAME = "gemini-2.5-flash"


def extract_json_from_response(response_text: str) -> dict:
    """
    Extract and parse JSON from model response, handling various formats.
    """
    text = response_text.strip()
    
    # Try direct JSON parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Remove markdown code blocks
    if "```" in text:
        # Extract content between code blocks
        pattern = r"```(?:json)?\s*([\s\S]*?)```"
        matches = re.findall(pattern, text)
        if matches:
            text = matches[0].strip()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
    
    # Try to find JSON object pattern
    json_pattern = r'\{[\s\S]*\}'
    matches = re.findall(json_pattern, text)
    
    # Try each match, starting with the longest (most complete)
    for match in sorted(matches, key=len, reverse=True):
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            # Try to fix common issues
            fixed = match
            # Fix unescaped newlines in strings
            fixed = re.sub(r'(?<!\\)\n', '\\n', fixed)
            # Fix trailing commas
            fixed = re.sub(r',(\s*[}\]])', r'\1', fixed)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                continue
    
    # Last resort: extract key fields manually
    result = {}
    
    # Extract classification
    class_match = re.search(r'"classification"\s*:\s*"(EDIBLE|NOT-EDIBLE)"', text, re.IGNORECASE)
    if class_match:
        result["classification"] = class_match.group(1).upper()
    
    # Extract decision
    decision_match = re.search(r'"decision"\s*:\s*"(SAFE_FOR_DONATION|SAFE_WITH_ADVISORY|DISCARD)"', text, re.IGNORECASE)
    if decision_match:
        result["decision"] = decision_match.group(1).upper()
    
    # Extract risk level
    risk_match = re.search(r'"risk_level"\s*:\s*"(VERY_LOW|LOW|MODERATE|HIGH|VERY_HIGH)"', text, re.IGNORECASE)
    if risk_match:
        result["risk_level"] = risk_match.group(1).upper()
    
    # Extract confidence
    conf_match = re.search(r'"confidence"\s*:\s*([\d.]+)', text)
    if conf_match:
        result["confidence"] = float(conf_match.group(1))
    
    if result:
        return result
    
    raise json.JSONDecodeError("Could not extract valid JSON from response", text, 0)


def analyze_food_image(
    image_bytes: bytes,
    preparation_time: str,
    package_time: str,
    mime_type: str = "image/jpeg"
) -> dict:
    """
    Analyze a food image for safety and donation eligibility.
    
    Args:
        image_bytes: Raw bytes of the food image
        preparation_time: ISO format datetime string of when food was prepared
        package_time: ISO format datetime string of when food was packaged
        mime_type: MIME type of the image (default: image/jpeg)
    
    Returns:
        dict containing:
            - classification: "EDIBLE" or "NOT-EDIBLE"
            - confidence: float between 0.0 and 1.0
            - reasoning: dict with detailed analysis
            - decision: "SAFE_FOR_DONATION", "SAFE_WITH_ADVISORY", or "DISCARD"
            - risk_level: Risk category string
            - advisory: Optional handling instructions
            - analyzedAt: ISO timestamp of analysis
    """
    response_text = ""
    
    try:
        # Parse times for context
        prep_dt = datetime.fromisoformat(preparation_time.replace('Z', '+00:00'))
        pkg_dt = datetime.fromisoformat(package_time.replace('Z', '+00:00'))
        current_dt = datetime.now()
        
        # Calculate time elapsed
        hours_since_prep = (current_dt - prep_dt).total_seconds() / 3600
        hours_since_pkg = (current_dt - pkg_dt).total_seconds() / 3600
        
        # Build the user prompt with context - emphasize JSON format
        user_prompt = f"""Analyze this food image for donation safety.

**Time Context:**
- Preparation Time: {preparation_time}
- Packaging Time: {package_time}
- Current Time: {current_dt.isoformat()}
- Hours since preparation: {hours_since_prep:.1f} hours
- Hours since packaging: {hours_since_pkg:.1f} hours

Evaluate this food item following the 6-step FSSAI evaluation pipeline.

CRITICAL: Respond with ONLY a valid JSON object. No markdown, no code blocks, no explanation text.
Use this exact structure:
{{"classification": "EDIBLE" or "NOT-EDIBLE", "decision": "SAFE_FOR_DONATION" or "SAFE_WITH_ADVISORY" or "DISCARD", "risk_level": "VERY_LOW" or "LOW" or "MODERATE" or "HIGH" or "VERY_HIGH", "confidence": 0.0 to 1.0, "reasoning": {{"visual_inspection": "...", "food_identification": "...", "time_temperature": "...", "protective_factors": "...", "donation_context": "...", "final_assessment": "..."}}, "advisory": null or "..."}}"""

        # Initialize the model
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=get_system_prompt()
        )
        
        # Create the image part
        image_part = {
            "mime_type": mime_type,
            "data": base64.b64encode(image_bytes).decode("utf-8")
        }
        
        # Generate response with JSON mode
        response = model.generate_content(
            [user_prompt, image_part],
            generation_config={
                "temperature": 0.1,
                "top_p": 0.95,
                "max_output_tokens": 2048,
                "response_mime_type": "application/json",
            }
        )
        
        response_text = response.text.strip()
        
        # Parse the response using robust extraction
        result = extract_json_from_response(response_text)
        
        # Add analysis timestamp
        result["analyzedAt"] = datetime.now().isoformat()
        
        # Ensure required fields exist with defaults
        if "classification" not in result:
            if result.get("decision") == "DISCARD":
                result["classification"] = "NOT-EDIBLE"
            elif result.get("decision") == "SAFE_FOR_DONATION":
                result["classification"] = "EDIBLE"
            else:
                result["classification"] = "NOT-EDIBLE"
        
        if "confidence" not in result:
            result["confidence"] = 0.5
        
        if "reasoning" not in result:
            result["reasoning"] = {"final_assessment": "Analysis completed"}
        
        if "risk_level" not in result:
            result["risk_level"] = "MODERATE"
        
        if "decision" not in result:
            result["decision"] = "SAFE_FOR_DONATION" if result["classification"] == "EDIBLE" else "DISCARD"
        
        return result
        
    except json.JSONDecodeError as e:
        return {
            "classification": "NOT-EDIBLE",
            "decision": "DISCARD",
            "risk_level": "HIGH",
            "confidence": 0.0,
            "reasoning": {
                "final_assessment": f"Analysis failed due to response parsing error: {str(e)}",
                "raw_response": response_text[:500] if response_text else "No response"
            },
            "advisory": "Manual review required - automated analysis failed",
            "analyzedAt": datetime.now().isoformat(),
            "error": True
        }
        
    except Exception as e:
        return {
            "classification": "NOT-EDIBLE",
            "decision": "DISCARD", 
            "risk_level": "HIGH",
            "confidence": 0.0,
            "reasoning": {
                "final_assessment": f"Analysis failed due to error: {str(e)}"
            },
            "advisory": "Manual review required - automated analysis failed",
            "analyzedAt": datetime.now().isoformat(),
            "error": True
        }
