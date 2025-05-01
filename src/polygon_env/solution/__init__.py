"""Code execution system for programming competition solutions."""

from .runners import LocalCompiledSolutionRunner, LocalInterpretedSolutionRunner, RunsSolution

# Move to singleton class?
_solution_runners_registry = {}


def register_solution_runner(
    lang: str | list[str],
    cmd: list[str],
    compiled: bool = False,
    aliases: list[str] | None = None,
):
    """
    Register a solution runner for one or more programming languages.

    Parameters
    ----------
    lang
        Language name or list of language names to register the runner for.
        Common examples: 'cpp', 'python', 'java'.
    cmd
        Command template for compiling/running solutions. Use placeholders:
        - {input_file}: Source file path
        - {output_file}: Compiled executable path (compiled only)
    compiled
        Whether the solution requires compilation (True) or is interpreted (False)
    aliases
        Optional list of additional language names that should use this runner

    Examples
    --------
    >>> register_solution_runner(
    ...     'c++',
    ...     ['c++', '-o', '{output_file}', '{input_file}'],
    ...     compiled=True,
    ...     aliases=['cpp']
    ... )
    >>> register_solution_runner(
    ...     'python',
    ...     ['python', '{input_file}'],
    ...     aliases=['py']
    ... )
    """

    if compiled:
        runner = LocalCompiledSolutionRunner(compiler_command=cmd)
    else:
        runner = LocalInterpretedSolutionRunner(run_command=cmd)

    aliases = aliases or []
    _solution_runners_registry[lang] = runner
    for lang_alias in aliases:
        _solution_runners_registry[lang_alias] = runner


def get_solution_runner(lang: str) -> RunsSolution:
    """
    Get the solution runner instance for a specific language.

    Parameters
    ----------
    lang
        Language name to look up in the registry

    Returns
    -------
    RunsSolution
        The solution runner instance registered for this language

    Raises
    ------
    KeyError
        If no runner is registered for the specified language

    Examples
    --------
    >>> runner = get_solution_runner('cpp')
    """
    try:
        return _solution_runners_registry[lang]
    except KeyError as e:
        raise ValueError(f'No solution runner registered for language {lang}') from e


register_solution_runner(
    'c++', cmd=['c++', '-o', '{output_file}', '{input_file}'], aliases=['cpp'], compiled=True
)
register_solution_runner('python', cmd=['python', '{input_file}'], aliases=['py'])

__all__ = [
    'get_solution_runner',
    'register_solution_runner',
]
