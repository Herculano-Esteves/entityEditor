
import re


def generate_unique_name(base_name: str, existing_names: set | list) -> str:
    """
    Generate a unique name by incrementing a trailing number.

    Examples:
        "Part" -> "Part1" if "Part" is taken
        "Part1" -> "Part2" if "Part1" is taken
    """
    if base_name not in existing_names:
        return base_name

    match = re.search(r'^(.*?)(\d+)$', base_name)
    if match:
        prefix = match.group(1)
        num = int(match.group(2))
    else:
        prefix = base_name
        num = 0

    while True:
        num += 1
        candidate = f"{prefix}{num}"
        if candidate not in existing_names:
            return candidate
