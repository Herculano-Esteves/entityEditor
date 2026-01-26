
import re

def generate_unique_name(base_name, existing_names):
    """
    Generates a unique name based on base_name.
    If base_name exists strings, appends _copy1, _copy2, etc.
    If base_name ends with _copyN, increments N.
    """
    if base_name not in existing_names:
        return base_name

    # Check for existing suffix pattern: name_copy(\d+) or just name_copy
    # User requested: _copy1, _copy2
    
    # Try to detect if we are duplicating an existing "copy"
    # Regex for ending with _copy(\d*)
    match = re.search(r'_copy(\d*)$', base_name)
    
    if match:
        # It's already a copy
        prefix = base_name[:match.start()] # "foo" from "foo_copy1"
        suffix_num_str = match.group(1) # "1" or ""
        
        if suffix_num_str:
            num = int(suffix_num_str)
            # Try incrementing
            while True:
                num += 1
                candidate = f"{prefix}_copy{num}"
                if candidate not in existing_names:
                    return candidate
        else:
            # It ended in _copy (no number), so try _copy1
            num = 1
            while True:
                candidate = f"{prefix}_copy{num}"
                if candidate not in existing_names:
                    return candidate
                num += 1
    else:
        # Fresh duplicate
        num = 1
        while True:
            candidate = f"{base_name}_copy{num}"
            if candidate not in existing_names:
                return candidate
            num += 1

def ensure_unique_name(name, existing_names):
    """
    Ensures name is unique among existing_names by appending number if needed.
    (Used for renaming collision)
    """
    if name not in existing_names:
        return name
        
    num = 1
    base = name
    
    # Check if name already has a number suffix?
    # User said "maybe force a number on the end"
    
    while True:
        candidate = f"{base}_{num}"
        if candidate not in existing_names:
            return candidate
        num += 1
