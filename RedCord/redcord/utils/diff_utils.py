from difflib import unified_diff


def create_diff(old: str, new: str) -> str:
    diff = unified_diff(old.splitlines(), new.splitlines(), fromfile="old", tofile="new", lineterm="")
    return "\n".join(diff)
