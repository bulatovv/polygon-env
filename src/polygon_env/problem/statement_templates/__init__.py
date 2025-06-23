import pathlib

from jinja2 import Environment, FileSystemLoader, StrictUndefined

here = pathlib.Path(__file__).parent.resolve()

jinja_env = Environment(loader=FileSystemLoader(str(here)), undefined=StrictUndefined)
jinja_env.globals['zip'] = zip  # pyright: ignore

statement_template = jinja_env.get_template('statement.md.jinja')

__all__ = ['statement_template']
