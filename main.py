from pathlib import Path

import chardet
import polars as pl
import yaml

from polygon_env.problem import Problem


def partition_files(filelist: list[str], N: int) -> list[list[str]]:
    """
    Partition files based on a component that satisfies range requirements.
    
    Parameters
    ----------
    filelist : list of str
        List of filenames with hyphen-separated components
    N : int
        Range parameter for partitioning
        
    Returns
    -------
    list of list of str
        N partitions, where partition i contains files with component value i+1 or chr(ord('A')+i)
    """
    if not filelist:
        return [[] for _ in range(N)]
    
    # Parse all filenames into components
    parsed_files = []
    max_components = 0
    
    for filename in filelist:
        # Remove file extension and split by hyphens
        base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        components = base_name.split('-')
        parsed_files.append((filename, components))
        max_components = max(max_components, len(components))
    
    # Find the component position that satisfies our requirements
    target_component_idx = None
    is_numerical = None
    
    for comp_idx in range(max_components):
        # Extract all values for this component position
        component_values = []
        for filename, components in parsed_files:
            if comp_idx < len(components):
                component_values.append(components[comp_idx])
        
        if not component_values:
            continue
            
        # Check if all values are numerical and in range [1, N]
        all_numerical = True
        numerical_values = []
        
        for value in component_values:
            if value.isdigit():
                num_val = int(value)
                if 1 <= num_val <= N:
                    numerical_values.append(num_val)
                else:
                    all_numerical = False
                    break
            else:
                all_numerical = False
                break
        
        if all_numerical and len(set(numerical_values)) > 1:
            target_component_idx = comp_idx
            is_numerical = True
            break
            
        # Check if all values are alphabetical and in range [A, A+N-1]
        all_alphabetical = True
        alphabetical_values = []
        
        for value in component_values:
            if len(value) == 1 and value.isupper() and value.isalpha():
                char_val = ord(value) - ord('A') + 1
                if 1 <= char_val <= N:
                    alphabetical_values.append(value)
                else:
                    all_alphabetical = False
                    break
            else:
                all_alphabetical = False
                break
        
        if all_alphabetical and len(set(alphabetical_values)) > 1:
            target_component_idx = comp_idx
            is_numerical = False
            break
    
    # If no suitable component found, return empty partitions
    if target_component_idx is None:
        return [[] for _ in range(N)]
    
    # Create partitions
    partitions = [[] for _ in range(N)]
    
    for filename, components in parsed_files:
        if target_component_idx < len(components):
            component_value = components[target_component_idx]
            
            if is_numerical and component_value.isdigit():
                partition_idx = int(component_value) - 1
                if 0 <= partition_idx < N:
                    partitions[partition_idx].append(filename)
            elif not is_numerical and len(component_value) == 1 and component_value.isupper():
                partition_idx = ord(component_value) - ord('A')
                if 0 <= partition_idx < N:
                    partitions[partition_idx].append(filename)
    
    return partitions

def detect_encoding(file_path: str | Path) -> str:
    """
    Detect the encoding of a file using chardet.
    
    Parameters
    ----------
    file_path : Union[str, Path]
        Path to the file to analyze
        
    Returns
    -------
    str
        Detected encoding name
    """
    with open(file_path, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        return result['encoding'] or 'utf-8'


def main():
    export_path = Path('./export_data')
    if not export_path.exists():
        export_path.mkdir()


    data_dir = Path('data/')
    for year_dir in data_dir.iterdir():
        for competition_dir in year_dir.iterdir():
            with (competition_dir / 'metadata.yml').open() as metadata_file:
                metadata = yaml.safe_load(metadata_file)
            

            problems_dir = competition_dir / 'problems'
            submissions_dir = competition_dir / 'submissions'
            submissions_separated = partition_files(
                list(map(str, submissions_dir.iterdir())),
                N=len(list(problems_dir.iterdir()))
            )

            for problem_dir, submission_files in zip(
                sorted(problems_dir.iterdir()),
                submissions_separated,
                strict=True
            ):
                output_df_path = (
                    export_path /
                    f'{year_dir.name}_{competition_dir.name}_{problem_dir.name}.parquet'
                )
                if output_df_path.exists():
                    continue


                row = {
                    'shortname': competition_dir.name,
                    'year': year_dir.name,
                    'stage': metadata['stage'],
                    'level': metadata['level'],
                    'link': metadata['link']
                }

                problem = Problem.from_directory(problem_dir)
                submissions = []
                for submission_file in map(Path, submission_files):
                    detected_encoding = detect_encoding(submission_file)
                    with submission_file.open(encoding=detected_encoding) as f:
                        submissions.append({
                            'name': submission_file.name,
                            'content': f.read()
                        })

                row |= {
                    'submissions': submissions,
                    'test_inputs': problem.test_inputs,
                    'test_outputs': problem.test_outputs,
                    'checker_code': problem.checker_code,
                    'max_memory_bytes': problem.max_memory_bytes,
                    'timeout_ms': problem.timeout_ms,
                    'input_file_name': problem.input_file_name,
                    'output_file_name': problem.output_file_name
                }

                if 'russian' in problem.languages:
                    row |= {
                        'statement_ru': problem.get_statement_md('russian'),
                        'tutorial_ru': problem.get_turotial_md('russian')
                    }

                if 'english' in problem.languages:
                    row |= { 
                        'statement_en': problem.get_statement_md('english'),
                        'tutorial_en': problem.get_turotial_md('english')
                    }
                
                row |= {
                    'images': [
                        {'bytes': v, 'path': k}
                        for k, v in problem.images
                    ]
                }

                df = pl.from_dicts(
                    [row],
                    schema=[
                        'statement_ru',
                        'tutorial_ru',
                        'statement_en',
                        'tutorial_en',
                        'images',
                        'max_memory_bytes',
                        'timeout_ms',
                        'input_file_name',
                        'output_file_name',
                        'test_inputs',
                        'test_outputs',
                        'submissions',
                        'checker_code',
                        'year',
                        'shortname',
                        'stage',
                        'level',
                        'link'
                    ]
                )
                df.write_parquet(output_df_path, compression='zstd', compression_level=12)


if __name__ == '__main__':
    main()
