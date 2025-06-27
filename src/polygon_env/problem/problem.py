import xml.etree.ElementTree as ET
from functools import cached_property
from pathlib import Path
from typing import NotRequired, TypedDict

import pypandoc

from polygon_env.checker.checker import ChecksSolution, LocalChecker
from polygon_env.problem.statement_templates import statement_template


class StatementSections(TypedDict):
    """Sections for problem statements"""

    name: str
    legend: str
    input: NotRequired[str]
    output: NotRequired[str]
    interaction: NotRequired[str]
    examples: tuple[list[str], list[str]]
    notes: NotRequired[str]
    # TODO: scroring.tex
    # TODO: use union type for sections of interactive and non-interactive problems


class Problem:
    def __init__(
        self,
        test_inputs: list[str],
        test_outputs: list[str],
        checker_code: str,
        max_memory_bytes: int,
        timeout_ms: int,
        tutorial: dict[str, str],
        statement_sections: dict[str, StatementSections],
        input_file_name: str | None,
        output_file_name: str | None,
        images: dict[str, bytes],
    ):
        self.test_inputs: list[str] = test_inputs
        self.test_outputs: list[str] = test_outputs
        self.checker_code: str = checker_code
        self.max_memory_bytes: int = max_memory_bytes
        self.timeout_ms: int = timeout_ms
        self.tutorial: dict[str, str] = tutorial
        self.statement_sections: dict[str, StatementSections] = statement_sections
        self.input_file_name: str | None = input_file_name
        self.output_file_name: str | None = output_file_name
        self.images: dict[str, bytes] = images

    @staticmethod
    def from_directory(problem_dir: Path):
        test_inputs, test_outputs = Problem._get_tests_or_examples(problem_dir / 'tests')
        with (problem_dir / 'check.cpp').open() as checker_file:
            checker_code = checker_file.read()

        with (problem_dir / 'problem.xml').open() as problem_xml_file:
            xml_root = ET.fromstring(problem_xml_file.read())

        limits = Problem._parse_limits(xml_root)  # pyright: ignore
        timeout_ms = limits['timeout_ms']
        max_memory_bytes = limits['max_memory_bytes']

        input_file_name, output_file_name = Problem._extract_io_filenames(xml_root)

        tutorial, statement_sections = Problem._get_tutorial_and_sections(
            problem_dir, languages=['russian', 'english']
        )

        images = Problem._get_images(problem_dir)

        return Problem(
            test_inputs=test_inputs,
            test_outputs=test_outputs,
            checker_code=checker_code,
            max_memory_bytes=max_memory_bytes,
            timeout_ms=timeout_ms,
            tutorial=tutorial,
            statement_sections=statement_sections,
            input_file_name=input_file_name,
            output_file_name=output_file_name,
            images=images,
        )

    @cached_property
    def is_interactive(self) -> bool:
        for lang in ['russian', 'english']:
            if lang in self.statement_sections and self.statement_sections[lang].get(
                'interaction'
            ):
                return True
        return False

    @cached_property
    def languages(self) -> list[str]:
        return list(self.statement_sections.keys())

    def get_checker(self) -> ChecksSolution:
        if self.is_interactive:
            raise RuntimeError('Checking interactive problems is not supported yet!')

        return LocalChecker(
            checker_code=self.checker_code,
            test_inputs=self.test_inputs,
            test_outputs=self.test_outputs,
        )

    def _convert_md(self, text: str):
        return pypandoc.convert_text(text, 'markdown', format='tex')

    def get_statement_md(self, lang) -> str:
        md_sections = self.statement_sections[lang]
        md_sections['name'] = self._convert_md(md_sections['name'])
        md_sections['legend'] = self._convert_md(md_sections['legend'])
        if md_sections.get('notes'):
            md_sections['notes'] = self._convert_md(md_sections['notes'])  # pyright: ignore
        if md_sections.get('input'):
            md_sections['input'] = self._convert_md(md_sections['input'])  # pyright: ignore
        if md_sections.get('output'):
            md_sections['output'] = self._convert_md(md_sections['output'])  # pyright: ignore

        return statement_template.render(problem=self, sections=md_sections, lang=lang)

    def get_turotial_md(self, lang) -> str | None:
        md_tutorial = self.tutorial.get(lang)
        if not md_tutorial:
            return None
        return self._convert_md(md_tutorial)

    @staticmethod
    def _get_images(problem_dir: Path) -> dict[str, bytes]:
        images_file_names = []
        sections_dir = problem_dir / 'statement-sections' / 'russian'
        if not sections_dir.exists():
            sections_dir = problem_dir / 'statement-sections' / 'english'

        for pattern in ['*.jpg', '*.jpeg', '*.png']:
            images_file_names.extend(sections_dir.glob(pattern))

        return {img_file_name.name: img_file_name.read_bytes() for img_file_name in images_file_names}

    @staticmethod
    def _parse_limits(xml_root: ET.ElementTree):
        testset = xml_root.find('.//testset')
        if testset is None:
            raise ValueError('No testset element found in problem.xml')

        time_limit_str = testset.get('time-limit')
        memory_limit_str = testset.get('memory-limit')
        if not (time_limit_str and memory_limit_str):
            time_limit_str = testset.find('time-limit').text
            memory_limit_str = testset.find('memory-limit').text

        if not (time_limit_str and memory_limit_str):
            raise ValueError('Time and memory limits not specified for this problem')

        if time_limit_str.endswith('s'):
            timeout_ms = int(float(time_limit_str[:-1]) * 1000)
        else:
            timeout_ms = int(time_limit_str)

        max_memory_bytes = int(memory_limit_str)

        return {'max_memory_bytes': max_memory_bytes, 'timeout_ms': timeout_ms}

    @staticmethod
    def _extract_io_filenames(xml_root) -> tuple[str | None, str | None]:
        """
        Extract input and output file names from problem XML.

        Returns
        -------
        tuple[str | None, str | None]
            Tuple of (input_filename, output_filename). Returns None for each
            if values empty or not found.
        """
        judging_element = xml_root.find('judging')
        if judging_element is None:
            return None, None

        input_file = judging_element.get('input-file')
        output_file = judging_element.get('output-file')

        # Convert empty strings to None for consistency
        input_file = input_file if input_file else None
        output_file = output_file if output_file else None

        return input_file, output_file

    @staticmethod
    def _get_tutorial_and_sections(problem_dir: Path, languages: list[str]):
        tutorial: dict[str, str] = {}
        statement_sections: dict[str, StatementSections] = {}

        for lang in languages:
            sections_dir = problem_dir / 'statement-sections' / lang
            if not sections_dir.exists():
                continue
            else:
                statement_sections[lang] = {}  # pyright: ignore

            if (sections_dir / 'tutorial.tex').exists():
                with (sections_dir / 'tutorial.tex').open() as tutorial_file:
                    tutorial[lang] = tutorial_file.read()

            with (sections_dir / 'name.tex').open() as name_file:
                statement_sections[lang]['name'] = name_file.read()

            with (sections_dir / 'legend.tex').open() as legend_file:
                statement_sections[lang]['legend'] = legend_file.read()

            if (sections_dir / 'input.tex').exists():
                with (sections_dir / 'input.tex').open() as input_format_file:
                    statement_sections[lang]['input'] = input_format_file.read()

            if (sections_dir / 'output.tex').exists():
                with (sections_dir / 'output.tex').open() as output_format_file:
                    statement_sections[lang]['output'] = output_format_file.read()

            if (sections_dir / 'interaction.tex').exists():
                with (sections_dir / 'interaction.tex').open() as interaction_file:
                    statement_sections[lang]['interaction'] = interaction_file.read()

            statement_sections[lang]['examples'] = Problem._get_tests_or_examples(sections_dir)

            if (sections_dir / 'notes.tex').exists():
                with (sections_dir / 'notes.tex').open() as notes_file:
                    statement_sections[lang]['notes'] = notes_file.read()

        return tutorial, statement_sections

    @staticmethod
    def _get_tests_or_examples(target_path: Path) -> tuple[list[str], list[str]]:
        """Find test inputs and outputs by first collecting output files, then finding corresponding inputs.

        Returns
        -------
        tuple[list[str], list[str]]
            A tuple containing lists of input content and output content respectively.
        """
        if not target_path.exists():
            raise RuntimeError('Cannot find tests or examples for this problem')
        inputs = []
        outputs = []

        # Collect output files first (files ending with .a)
        output_files = sorted(
            [f for f in target_path.iterdir() if f.is_file() and f.name.endswith('.a')]
        )

        for output_file in output_files:
            # Read output file
            output_content = output_file.read_text()
            outputs.append(output_content)

            # Find corresponding input file (remove .a extension)
            input_file_name = output_file.name[:-2]  # Remove '.a' suffix
            input_file = target_path / input_file_name

            if input_file.exists():
                input_content = input_file.read_text()
                inputs.append(input_content)
            else:
                raise RuntimeError(f'Test input not found for test output {output_file}')

        return inputs, outputs
