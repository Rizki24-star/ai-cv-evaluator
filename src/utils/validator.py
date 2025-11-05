import json
import re
import logging
from typing import Dict, Any, Type
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


def validate_and_repair_json(
    json_str: str,
    expected_model: Type[BaseModel]
) -> Dict[str, Any]:
    """
    Validate LLM JSON output and attempt repair if broken
    """

    try:
        data = json.loads(json_str)
        data = normalize_json_fields(data)
        data = validate_score_range(data)
        validated = expected_model(**data)
        return validated.model_dump()
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON, attempting repair: {e}")
    except ValidationError as e:
        logger.warning(f"Validation failed on first attempt: {e}")
        # Continue to repair steps

    # Clean common issues
    cleaned = clean_json_string(json_str)

    try:
        data = json.loads(cleaned)
        data = normalize_json_fields(data)
        data = validate_score_range(data)
        validated = expected_model(**data)
        logger.info("JSON repaired successfully after cleaning")
        return validated.model_dump()
    except (json.JSONDecodeError, ValidationError):
        logger.warning("Cleaning failed, attempting regex extraction")

    # Extract with regex as last resort
    try:
        extracted = extract_json_with_regex(json_str, expected_model)
        extracted = normalize_json_fields(extracted)
        extracted = validate_score_range(extracted)
        validated = expected_model(**extracted)
        logger.info("JSON extracted with regex successfully")
        return validated.model_dump()
    except ValidationError as e:
        logger.warning(f"Regex extraction incomplete: {e}")


    # Fill missing fields with defaults
    try:
        partial_data = extract_json_with_regex(json_str, expected_model)
        complete_data = fill_missing_fields(partial_data, expected_model)
        complete_data = normalize_json_fields(complete_data)
        complete_data = validate_score_range(complete_data)
        validated = expected_model(**complete_data)
        logger.info("JSON completed with defaults")
        return validated.model_dump()
    except Exception as e:
        logger.error(f"All repair attempts failed: {e}")
        raise ValueError(f"Cannot parse or repair JSON: {e}")


def clean_json_string(json_str: str) -> str:
    """
    Clean common JSON formatting issues from LLM output
    """
    # Remove markdown code blocks
    cleaned = re.sub(r'```json\s*', '', json_str)
    cleaned = re.sub(r'```\s*', '', cleaned)

    # Remove leading/trailing whitespace
    cleaned = cleaned.strip()

    # Fix trailing commas before closing brackets
    cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)

    # Fix missing commas between properties
    cleaned = re.sub(r'"\s*\n\s*"', '",\n"', cleaned)

    # Remove comments (single line and multi-line)
    cleaned = re.sub(r'//.*?\n', '\n', cleaned)
    cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)

    return cleaned


def extract_json_with_regex(text: str, model: Type[BaseModel]) -> Dict[str, Any]:
    """
    Extract JSON-like content with regex as last resort
    """
    result = {}

    # Get expected fields from model
    model_fields = model.model_fields

    # Extract integer scores (1-5)
    score_pattern = r'"?(\w+)"?\s*:\s*(\d)'
    for match in re.finditer(score_pattern, text):
        field, value = match.groups()
        if field in model_fields:
            try:
                result[field] = int(value)
            except ValueError:
                continue

    # Extract float values
    float_pattern = r'"?(\w+)"?\s*:\s*(\d+\.?\d*)'
    for match in re.finditer(float_pattern, text):
        field, value = match.groups()
        if field in model_fields and field not in result:
            try:
                result[field] = float(value)
            except ValueError:
                continue

    # Extract string values (in quotes)
    string_pattern = r'"(\w+)"\s*:\s*"([^"]*)"'
    for match in re.finditer(string_pattern, text):
        field, value = match.groups()
        if field in model_fields:
            result[field] = value

    # Extract multi-line string values
    multiline_pattern = r'"(\w+)"\s*:\s*"([^"]*(?:\n[^"]*)*)"'
    for match in re.finditer(multiline_pattern, text):
        field, value = match.groups()
        if field in model_fields and field not in result:
            result[field] = value.replace('\n', ' ').strip()

    return result


def fill_missing_fields(data: Dict[str, Any], model: Type[BaseModel]) -> Dict[str, Any]:
    """
    Fill missing fields with sensible defaults
    """
    complete_data = data.copy()

    for field_name, field_info in model.model_fields.items():
        if field_name not in complete_data:
            # Get default value based on type
            default_value = get_default_value(field_name, field_info)
            complete_data[field_name] = default_value
            logger.warning(f"Field '{field_name}' missing, using default: {default_value}")

    return complete_data


def get_default_value(field_name: str, field_info: Any) -> Any:
    """
    Get sensible default value for a field
    """
    # Check if field has a default
    if field_info.default is not None:
        return field_info.default

    # Infer from field name and type
    annotation = field_info.annotation

    # Handle Optional types
    if hasattr(annotation, '__origin__') and annotation.__origin__ is type(None):
        return None

    # Score fields default to middle value (3)
    if 'score' in field_name.lower() or field_name in [
        'technical_skills', 'experience_level', 'achievements', 'cultural_fit',
        'correctness', 'code_quality', 'resilience', 'documentation', 'creativity'
    ]:
        return 3

    # Feedback fields default to placeholder
    if 'feedback' in field_name.lower() or 'summary' in field_name.lower():
        return "Evaluation incomplete - please review manually"

    # Rate/percentage fields
    if 'rate' in field_name.lower():
        return 0.6  # 60% conservative default

    # String fields
    if annotation == str:
        return ""

    # Integer fields
    if annotation == int:
        return 0

    # Float fields
    if annotation == float:
        return 0.0

    # Default to None for unknown types
    return None


def normalize_json_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize common LLM JSON deviations:
    - Convert numeric-like strings to numbers for known score fields and nested 'scores'
    - Ensure 'reasoning' is a dict (wrap string/list into {'summary': ...})
    - Trim text fields for cleanliness
    """
    if not isinstance(data, dict):
        return data

    # Coerce numeric-like strings for known fields
    score_fields = {
        'technical_skills', 'experience_level', 'achievements', 'cultural_fit',
        'correctness', 'code_quality', 'resilience', 'documentation', 'creativity'
    }

    def coerce_num(val):
        if isinstance(val, (int, float)):
            return val
        if isinstance(val, str):
            s = val.strip()
            # Extract leading number if present
            m = re.match(r"^(-?\d+(?:\.\d+)?)", s)
            if not m:
                # Fallback: find any number in the string (prefer 1-5)
                m = re.search(r"(?<!\d)([1-5])(?!\d)", s) or re.search(r"(-?\d+(?:\.\d+)?)", s)
            if m:
                num_str = m.group(1)
                try:
                    if "." in num_str:
                        return float(num_str)
                    return int(num_str)
                except Exception:
                    return val
        return val

    for k in list(data.keys()):
        v = data[k]
        if k in score_fields:
            data[k] = coerce_num(v)
        elif k == 'scores' and isinstance(v, dict):
            for sk, sv in list(v.items()):
                if sk in score_fields:
                    v[sk] = coerce_num(sv)
        elif isinstance(v, str):
            data[k] = v.strip()

    # Normalize reasoning to a dict
    if 'reasoning' in data:
        rv = data['reasoning']
        if isinstance(rv, str) and rv.strip():
            data['reasoning'] = {'summary': rv.strip()}
        elif isinstance(rv, list):
            # Join list into a summary and map index to items
            summary = "; ".join([str(x).strip() for x in rv if str(x).strip()])
            detailed = {f"item_{i+1}": str(x).strip() for i, x in enumerate(rv)}
            data['reasoning'] = {'summary': summary, 'details': detailed}
        elif rv is None:
            data['reasoning'] = {}
    else:
        # If model expects reasoning but it's missing, leave it absent; fill_missing_fields may add default
        pass

    return data


def validate_score_range(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure all score fields are within 1-5 range
    """
    score_fields = [
        'technical_skills', 'experience_level', 'achievements', 'cultural_fit',
        'correctness', 'code_quality', 'resilience', 'documentation', 'creativity'
    ]

    for field in score_fields:
        if field in data:
            value = data[field]
            if not isinstance(value, (int, float)):
                continue

            # Clamp to 1-5 range
            if value < 1:
                logger.warning(f"{field} score {value} below minimum, setting to 1")
                data[field] = 1
            elif value > 5:
                logger.warning(f"{field} score {value} above maximum, setting to 5")
                data[field] = 5
            else:
                # Round to nearest integer
                data[field] = round(value)

    return data
