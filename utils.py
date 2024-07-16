def encode_unicode_escape(s: str) -> str:
    "Because we remove backslashes when parsing, then we must fix these slashes when we take a unicode word"
    return r"".join('\\' + char if char == 'u' else char for char in s)


def get_fixed_unicode_escape(s: str) -> str:
    fixed = encode_unicode_escape(s)
    return bytes(fixed, "utf-8").decode("unicode-escape")


def binary_search_by_names(sorted_stations: list[dict], name: str) -> dict | None:
    target = int(name)
    left = 0
    right = len(sorted_stations) - 1
    while left <= right:
        mid = (left + right) // 2
        mid_value = int(sorted_stations[mid]['name'])

        if mid_value == target:
            return sorted_stations[mid]
        elif mid_value < target:
            left = mid + 1
        else:
            right = mid - 1
    return None
