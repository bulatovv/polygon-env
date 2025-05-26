from typing import Literal, TypeAlias, TypedDict


class _AcceptedResult(TypedDict):
    outcome: Literal['accepted']
    message: str


class _WrongAnswerResult(TypedDict):
    outcome: Literal['wrong-answer']
    message: str


class _PresentationErrorResult(TypedDict):
    outcome: Literal['presentation-error']
    message: str


class _PointsResult(TypedDict):
    outcome: Literal['points']
    points: float
    message: str


class _PartiallyCorrectResult(TypedDict):
    outcome: Literal['partially-correct']
    type: int


class _TimeLimitExceedResult(TypedDict):
    outcome: Literal['time-limit-exceed']
    limit: int


class _MemoryLimitExceedResult(TypedDict):
    outcome: Literal['memory-limit-exceed']
    limit: int


class _RuntimeErrorResult(TypedDict):
    outcome: Literal['runtime-error']
    exit_code: int
    stderr: str


class _CompilationErrorResult(TypedDict):
    outcome: Literal['compilation-error']
    exit_code: int
    stderr: str


CheckResult: TypeAlias = (
    _AcceptedResult
    | _WrongAnswerResult
    | _PresentationErrorResult
    | _PointsResult
    | _PartiallyCorrectResult
)

CheckResultOrError: TypeAlias = (
    CheckResult
    | _TimeLimitExceedResult
    | _MemoryLimitExceedResult
    | _RuntimeErrorResult
    | _CompilationErrorResult
)
