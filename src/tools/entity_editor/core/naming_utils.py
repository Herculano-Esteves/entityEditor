
import re

def generate_unique_name(base_name, existing_names):
    """
    Generates a unique name by incrementing a trailing number.
    e.g. thing -> thing1, thing1 -> thing2.
    """
    if base_name not in existing_names:
        return base_name

    # Check for existing numeric suffix
    # Group 1: Base (non-digit suffix, but strict split)
    # Group 2: Number
    match = re.search(r'^(.*?)(\d+)$', base_name)
    
    if match:
        prefix = match.group(1)
        num = int(match.group(2))
    else:
        prefix = base_name
        num = 0
    
    # Iterate until we find a free number
    while True:
        num += 1
        candidate = f"{prefix}{num}"
        if candidate not in existing_names:
            return candidate

def ensure_unique_name(name, existing_names):
    """
    Ensures name is unique. Uses the same natural increment logic.
    """
    return generate_unique_name(name, existing_names)
