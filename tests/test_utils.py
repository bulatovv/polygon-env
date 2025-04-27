from polygon_env.utils import format_list


class _SafeDict(dict[str, str]):
    def __missing__(self, key):
        return '{' + key + '}'


def test_basic_formatting():
    """Test basic placeholder replacement."""
    result = format_list(['abc', '{foo}', '{bar}'], foo='1', bar='2')
    assert result == ['abc', '1', '2']


def test_missing_placeholders_preserved():
    """Test that placeholders without matching keys remain unchanged."""
    result = format_list(['{baz}'], foo='1')
    assert result == ['{baz}']


def test_invalid_format_strings_preserved():
    """Test that invalid format strings are left unchanged."""
    result = format_list(['a{b'], foo='1')
    assert result == ['a{b']


def test_partial_formatting():
    """Test partial formatting where some placeholders are replaced."""
    result = format_list(['{foo} {bar}'], foo='42')
    assert result == ['42 {bar}']


def test_empty_list():
    """Test with empty input list."""
    result = format_list([], foo='bar')
    assert result == []


def test_no_kwargs():
    """Test with no keyword arguments provided."""
    result = format_list(['{foo}', 'bar', '{baz}'])
    assert result == ['{foo}', 'bar', '{baz}']


def test_strings_without_placeholders():
    """Test strings that don't contain any placeholders."""
    result = format_list(['hello', 'world', 'test'], foo='bar')
    assert result == ['hello', 'world', 'test']


def test_multiple_placeholders_same_string():
    """Test string with multiple placeholders."""
    result = format_list(['{name} is {age} years old'], name='Alice', age='25')
    assert result == ['Alice is 25 years old']


def test_multiple_placeholders_partial_match():
    """Test string with multiple placeholders where only some match."""
    result = format_list(
        ['{name} is {age} years old and lives in {city}'], name='Bob', age='30'
    )
    assert result == ['Bob is 30 years old and lives in {city}']


def test_numeric_values():
    """Test with numeric values converted to strings."""
    result = format_list(['{count} items', '{price}'], count=42, price=19.99)
    assert result == ['42 items', '19.99']


def test_duplicate_placeholders():
    """Test string with duplicate placeholders."""
    result = format_list(['{greeting} {name}, {greeting}!'], greeting='Hello', name='World')
    assert result == ['Hello World, Hello!']


def test_nested_braces():
    """Test strings with nested or complex brace patterns."""
    result = format_list(['{{not_a_placeholder}}', '{{{foo}}}'], foo='bar')
    assert result == ['{not_a_placeholder}', '{bar}']


def test_escaped_braces():
    """Test strings with escaped braces."""
    result = format_list(['{{foo}}', '{foo}'], foo='bar')
    assert result == ['{foo}', 'bar']


def test_invalid_format_strings():
    """Test various invalid format string patterns."""
    invalid_strings = [
        'a{b',  # unmatched opening brace
        'a}b',  # unmatched closing brace
        'a{b}c}d',  # extra closing brace
        'a{b{c}d',  # nested opening brace
        '{',  # single opening brace
        '}',  # single closing brace
        '{}',  # empty placeholder
    ]
    result = format_list(invalid_strings, b='replaced', c='test')
    # All should remain unchanged due to invalid format
    assert result == invalid_strings


def test_empty_strings():
    """Test with empty strings in the list."""
    result = format_list(['', '{foo}', ''], foo='bar')
    assert result == ['', 'bar', '']


def test_whitespace_in_placeholders():
    """Test placeholders with whitespace."""
    result = format_list(['{foo bar}'], **{'foo bar': 'test'})
    assert result == ['test']


def test_special_characters_in_values():
    """Test values containing special characters."""
    result = format_list(['{special}'], special='$#@!%^&*()')
    assert result == ['$#@!%^&*()']


def test_unicode_characters():
    """Test with unicode characters in both placeholders and values."""
    result = format_list(['{émoji}', '{name}'], émoji='🎉', name='José')
    assert result == ['🎉', 'José']


def test_very_long_string():
    """Test with very long strings."""
    long_string = 'a' * 1000 + '{foo}' + 'b' * 1000
    expected = 'a' * 1000 + 'bar' + 'b' * 1000
    result = format_list([long_string], foo='bar')
    assert result == [expected]


def test_mixed_valid_invalid_strings():
    """Test mix of valid and invalid format strings."""
    strings = ['{valid}', 'a{invalid', '{another_valid}', 'no_placeholders']
    result = format_list(strings, valid='OK', another_valid='GOOD')
    assert result == ['OK', 'a{invalid', 'GOOD', 'no_placeholders']


def test_case_sensitive_placeholders():
    """Test that placeholder names are case sensitive."""
    result = format_list(['{foo}', '{Foo}', '{FOO}'], foo='lower', Foo='Title', FOO='UPPER')
    assert result == ['lower', 'Title', 'UPPER']


def test_return_new_list():
    """Test that function returns a new list, not modifying the original."""
    original = ['{foo}', 'bar']
    result = format_list(original, foo='baz')
    assert result == ['baz', 'bar']
    assert original == ['{foo}', 'bar']  # Original unchanged
    assert result is not original  # Different list objects
