class _SafeDict(dict[str, str]):
    def __missing__(self, key):
        return '{' + key + '}'


def format_list(string_list, **kwargs):
    """
    Format a list of strings, replacing placeholders with given values.

    Safely formats each string in the input list, leaving placeholders unchanged if their keys are missing.
    Invalid format strings (e.g., unmatched braces) are preserved as-is.

    Parameters
    ----------
    string_list : list of str
        List of strings containing optional placeholders (e.g., '{foo}').
    **kwargs
        Key-value pairs for placeholder substitution (e.g., foo=42 → replaces '{foo}' with '42').

    Returns
    -------
    list of str
        New list with formatted strings. Placeholders without matching keys remain unchanged.

    Examples
    --------
    >>> format_list(['abc', '{foo}', '{bar}'], foo=1, bar=2)
    ['abc', '1', '2']

    >>> format_list(['{baz}'], foo=1)
    ['{baz}']

    >>> format_list(['a{b'], foo=1)
    ['a{b']

    >>> format_list(['{foo} {bar}'], foo=42)
    ['42 {bar}']
    """
    safe_dict = _SafeDict(kwargs)
    result = []
    for s in string_list:
        try:
            # Format the string using the safe dictionary for missing keys
            result.append(s.format_map(safe_dict))
        except ValueError:
            # Leave the string unchanged on formatting errors (e.g., invalid syntax)
            result.append(s)
    return result
