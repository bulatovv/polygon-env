import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TypedDict

#name
#    timelim:
#    memlim:
#    input_file:
#    output_file:
#legend
#input -> Формат входных данных -> Input
#output-> Формат выходных данных -> Output
#examples -> Примеры (стандартный ввод/стандартный вывод) -> Examples (...)
#
#notes -> Замечание -> Note


class StatementSections(TypedDict):
    """Sections for problem statements"""
    name: str
    legend: str
    input: str
    output: str
    examples: tuple[
        list[str], list[str]
    ]
    notes: str
    # TODO: scroring?




class Problem:
    def __init__(
        self,
        test_inputs: list[str],
        test_outputs: list[str],
        checker_code: str,
        max_memory_bytes: int,
        timeout_ms: int,
        tutorial: dict[str, str],
        statement_sections: dict[str, StatementSections] 
    ):
        self.test_inputs: list[str] = test_inputs
        self.test_outputs: list[str] = test_outputs
        self.checker_code: str = checker_code
        self.max_memory_bytes: int = max_memory_bytes
        self.timeout_ms: int = timeout_ms
        self.tutorial: dict[str, str] = tutorial
        self.statement_sections: dict[str, StatementSections]

    @staticmethod
    def from_directory(problem_dir: Path):
        test_inputs, test_outputs = Problem._get_tests_or_examples(
            problem_dir / 'tests'
        )
        with (problem_dir / 'check.cpp').open() as checker_file:
            checker_code = checker_file.read()
      
        problem_xml_data = Problem._parse_problem_xml(problem_dir)
        timeout_ms = problem_xml_data['time-limit']
        max_memory_bytes = problem_xml_data['memory-limit']


    @staticmethod
    def _parse_problem_xml(problem_dir: Path):
        with (problem_dir / 'problem.xml').open() as problem_xml_file:
            problem_xml = problem_xml_file.read()
        root = ET.fromstring(problem_xml)
        
        testset = root.find('.//testset')
        if testset is None:
            raise ValueError("No testset element found in problem.xml")
        
        time_limit_str = testset.get('time-limit')
        memory_limit_str = testset.get('memory-limit')
        if not (time_limit_str and memory_limit_str):
            raise ValueError('Time and memory limits not specified for this problem')
        
        if time_limit_str.endswith('s'):
            timeout_ms = int(float(time_limit_str[:-1]) * 1000)
        else:
            raise ValueError(f'Unknown time limit format: {time_limit_str}')
        
        max_memory_bytes = int(memory_limit_str)

        return {
            'max_memory_bytes': max_memory_bytes,
            'timeout_ms': timeout_ms
        }


    @staticmethod
    def _get_tutorial_and_sections(problem_dir: Path, languages: list[str]):
        tutorial: dict[str, str] = {}
        statement_sections: dict[str, StatementSections]  = {}

        for lang in languages:
            sections_dir = problem_dir / 'statement-sections' / lang
            with (sections_dir / 'tutorial.tex').open() as tutorial_file:
                tutorial[lang] = tutorial_file.read()

            with (sections_dir / 'name.tex').open() as name_file:
                statement_sections[lang]['name'] = name_file.read()

            with (sections_dir / 'legend.tex').open() as legend_file:
                statement_sections[lang]['legend'] = legend_file.read()

            with (sections_dir / 'input.tex').open() as input_format_file:
                statement_sections[lang]['input'] = input_format_file.read()
            
            with (sections_dir / 'output.tex').open() as output_format_file:
                statement_sections[lang]['output'] = output_format_file.read()

            statement_sections[lang]['examples'] = Problem._get_tests_or_examples(sections_dir)

            with (sections_dir / 'notes.tex').open() as notes_file:
                statement_sections[lang]['notes'] = notes_file.read()

    @staticmethod
    def _get_tests_or_examples(target_path: Path) -> tuple[list[str], list[str]]:
        if not target_path.exists():
            raise RuntimeError("Cannot find tests or examples for this problem")

        inputs = []
        outputs = []

        # Collect test files (assuming numbered pattern like 01, 02, etc.)
        input_files = sorted(
            [
                f for f in target_path.iterdir()
                if f.is_file() and not f.name.endswith('.a')
                and not f.name.endswith('.tex')
            ]
        )

        for input_file in input_files:
            # Read input file
            input_content = input_file.read_text()
            inputs.append(input_content)

            # Read corresponding output file (.a extension)
            output_file = target_path / f'{input_file.name}.a'
            if output_file.exists():
                output_content = output_file.read_text()
                outputs.append(output_content)
            else:
                raise RuntimeError(f'Test output not specified for test input {input_file}')

        return inputs, outputs


