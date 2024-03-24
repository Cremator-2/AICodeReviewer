import asyncio
import os
import argparse
import pathlib
import logging
import shutil
from itertools import islice

from openai import AsyncOpenAI

__reviewer_folder_name__ = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
__local_path__ = pathlib.Path(__file__).parent.resolve()
__project_path__ = pathlib.Path(__file__).parent.parent.resolve()

DETAIL_ANALYSIS_PROMPT = f'{__local_path__}/prompts/detail.md'
SHORT_ANALYSIS_PROMPT = f'{__local_path__}/prompts/short.md'
PROJECT_ANALYSIS_PROMPT = f'{__local_path__}/prompts/project.md'

DETAIL_ANALYSIS_MD = 'detail_analysis.md'
SHORT_ANALYSIS_MD = 'short_analysis.md'
PROJECT_ANALYSIS_MD = 'project_analysis.md'

MODEL = 'gpt-4-0125-preview'
TEMPERATURE = .1
SEED = 66

REVIEWER_DIR_IN_PROJECT = '.reviewer'
LOG_FILE = f'{REVIEWER_DIR_IN_PROJECT}/logs.log'
NUMBER_OF_CONCURRENT_REQUESTS = 20

CANT_READ_FILE_MES = 'Can not read file'
NO_CHANGES = 'No changes required'

IGNORE_STARTS_WITH = ['.']
IGNORE_ENDS_WITH = ['.ipynb', '.md', '.log', '.lock']
IGNORE_EQUALS = ['venv', '__pycache__', 'logs', __reviewer_folder_name__, REVIEWER_DIR_IN_PROJECT]

MD_TITLE = '## '


def get_logger(
        name: str = __name__,
        logging_in_file: bool = False,
        logging_in_console: bool = True,
        file_log_level: int = logging.DEBUG,
        console_log_level: int = logging.INFO,
        formatter: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        log_file: str = LOG_FILE
) -> logging.Logger:

    _logger = logging.getLogger(name)
    _logger.setLevel(min(console_log_level, file_log_level))  # Set logger to the lower of the two levels

    # File handler for saving logs to a file
    if logging_in_file:
        file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        file_handler.setLevel(file_log_level)
        file_handler.setFormatter(logging.Formatter(formatter))
        _logger.addHandler(file_handler)

    # Stream handler for printing logs to console
    if logging_in_console:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(console_log_level)
        stream_handler.setFormatter(logging.Formatter(formatter))
        _logger.addHandler(stream_handler)

    return _logger


def project_tree(
        ignore_starts_with: list = None,
        ignore_ends_with: list = None,
        ignore_equals: list = None,
        dir_tree: str | os.PathLike = '..',
        level: int = 0,
        prefix: str = '',
):
    if ignore_starts_with is None:
        ignore_starts_with = IGNORE_STARTS_WITH
    if ignore_ends_with is None:
        ignore_ends_with = IGNORE_ENDS_WITH
    if ignore_equals is None:
        ignore_equals = IGNORE_EQUALS

    end = '\n'
    files_with_path = []

    def custom_sort(y):
        p = os.path.join(dir_tree, y)
        if os.path.isdir(p):
            return (1, y)
        else:
            return (0, y)

    def filter_items(
            _items: list,
            _starts_with: list,
            _ends_with: list,
            _equals: list,
    ) -> list:
        return [j for j in _items if not any([
            any(j.startswith(sw) for sw in _starts_with),
            any(j.endswith(ew) for ew in _ends_with),
            j in _equals,
        ])]

    items = os.listdir(dir_tree)
    items = filter_items(
        _items=items,
        _starts_with=ignore_starts_with,
        _ends_with=ignore_ends_with,
        _equals=ignore_equals,
    )

    p_tree = ''
    items.sort(key=custom_sort)
    for i, item in enumerate(items):
        path = os.path.join(dir_tree, item)
        is_last = i == len(items) - 1
        if os.path.isdir(path):
            if is_last:
                p_tree += prefix + '└─── ' + item + "/" + end
                subtree, subfiles = project_tree(
                    dir_tree=path,
                    level=level + 1,
                    prefix=prefix + '     ',
                    ignore_starts_with=ignore_starts_with,
                    ignore_ends_with=ignore_ends_with,
                    ignore_equals=ignore_equals
                )
                p_tree += subtree
                files_with_path.extend(subfiles)
            else:
                p_tree += prefix + '├─── ' + item + "/" + end
                subtree, subfiles = project_tree(
                    dir_tree=path,
                    level=level + 1,
                    prefix=prefix + '│    ',
                    ignore_starts_with=ignore_starts_with,
                    ignore_ends_with=ignore_ends_with,
                    ignore_equals=ignore_equals
                )
                p_tree += subtree
                files_with_path.extend(subfiles)
        else:
            if is_last:
                p_tree += prefix + '└─── ' + item + end
            else:
                p_tree += prefix + '├─── ' + item + end
            files_with_path.append(path)

    return p_tree, files_with_path


def clear_dir(directory: str):
    if os.path.exists(directory):
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
    else:
        os.makedirs(directory)


def read_file_content(file_path, base_dir, is_prompt=False):
    content = ''
    rel_path = os.path.relpath(file_path, base_dir)
    marker = '-' * 30
    title = f'{marker} {rel_path} {marker}\n'
    if not is_prompt:
        content += title
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content += f.read()
            content += '\n'
    except Exception as e:
        content = f"{title}{CANT_READ_FILE_MES}\n"
        logger.warning(f'Can not read file {rel_path}: {e}')
    return content, str(rel_path)


def write_to_md(name: str, data: str, directory: str):
    file_path = os.path.join(directory, name)
    with open(file_path, "a", encoding="utf-8") as file:
        file.write(data + "\n")


def to_openai_system_message(prompt: str) -> dict:
    return {"role": "system", "content": prompt}


def to_openai_user_message(prompt: str) -> dict:
    return {"role": "user", "content": prompt}


def to_openai_assistant_message(prompt: str) -> dict:
    return {"role": "assistant", "content": prompt}


def get_openai_client(key: str = None):
    if key:
        return AsyncOpenAI(api_key=key)
    else:
        return AsyncOpenAI()


async def openai_request(
        client: AsyncOpenAI,
        messages: list[dict],
        model: str = MODEL,
        temperature: float = TEMPERATURE,
        seed: int | None = None
) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        seed=seed
    )
    return response.choices[0].message.content


async def main(client: AsyncOpenAI, directory: str):

    def format_title(k: str, v: str) -> str:
        return MD_TITLE + k + '\n\n' + v

    def dict_to_batches(input_dict, batch_size):
        it = iter(input_dict.items())
        for _ in range(0, len(input_dict), batch_size):
            yield dict(islice(it, batch_size))

    async def task(k, v):
        return (k, await openai_request(
            client=client,
            messages=v,
            seed=SEED)
        )

    async def process_batch(b):
        tasks = []
        for k, v in b.items():
            logger.info(f'{k} in progress...')
            tasks.append(task(k, v))
        r = await asyncio.gather(*tasks)
        logger.info(f'Batch of files done. Elements in batch - {len(r)}')
        return r

    detail_analysis_prompt, _ = read_file_content(DETAIL_ANALYSIS_PROMPT, __local_path__, is_prompt=True)
    short_analysis_prompt, _ = read_file_content(SHORT_ANALYSIS_PROMPT, __local_path__, is_prompt=True)
    project_analysis_prompt, _ = read_file_content(PROJECT_ANALYSIS_PROMPT, __local_path__, is_prompt=True)

    tree, project_files = project_tree(
        ignore_starts_with=IGNORE_STARTS_WITH,
        ignore_ends_with=IGNORE_ENDS_WITH,
        ignore_equals=IGNORE_EQUALS,
        dir_tree=directory
    )
    logger.debug(f'Project tree:\n{tree}')
    logger.debug(f'Files:\n{project_files}')

    logger.info(f'Start of detailed review...')

    tree = MD_TITLE + 'Project tree:\n```\n' + tree + '```\n'
    write_to_md(name=DETAIL_ANALYSIS_MD, directory=REVIEWER_DIR_IN_PROJECT, data=tree)

    detail_analysis_prompt_dict = {}
    for f_path in project_files:
        file_detail_analysis, relative_path = read_file_content(file_path=f_path, base_dir=directory)

        if CANT_READ_FILE_MES in file_detail_analysis:
            continue

        messages = [
            to_openai_system_message(detail_analysis_prompt),
            to_openai_user_message(file_detail_analysis)
        ]
        detail_analysis_prompt_dict[relative_path] = messages

    batches = list(dict_to_batches(detail_analysis_prompt_dict, NUMBER_OF_CONCURRENT_REQUESTS))

    detail_analysis_result_dict = {}
    for batch in batches:
        results = await process_batch(batch)
        for key, result in results:
            result_formatted = format_title(k=key, v=result)
            logger.debug(f'AI file analysis {key}:\n{result_formatted}')
            write_to_md(name=DETAIL_ANALYSIS_MD, directory=REVIEWER_DIR_IN_PROJECT, data=result_formatted)
            detail_analysis_result_dict[key] = result_formatted

    logger.info(f'Start of short review...')

    short_analysis_prompt_dict = {}
    for key, value in detail_analysis_result_dict.items():
        messages = [
            to_openai_system_message(short_analysis_prompt),
            to_openai_system_message(value)
        ]
        short_analysis_prompt_dict[key] = messages

    batches = list(dict_to_batches(short_analysis_prompt_dict, NUMBER_OF_CONCURRENT_REQUESTS))

    files_analysis_results = []
    for batch in batches:
        results = await process_batch(batch)
        for key, result in results:
            result_formatted = format_title(k=key, v=result)
            logger.debug(f'AI file analysis {key}:\n{result_formatted}')

            if NO_CHANGES in result_formatted:
                continue

            write_to_md(name=SHORT_ANALYSIS_MD, directory=REVIEWER_DIR_IN_PROJECT, data=result_formatted)
            files_analysis_results.append(result_formatted)

    logger.info(f'Start of project review...')

    openai_messages = [to_openai_system_message(analysis) for analysis in files_analysis_results]

    project_system_messages = openai_messages.copy()
    project_system_messages.append(to_openai_system_message(project_analysis_prompt))

    project_analysis_result = await openai_request(
        client=client,
        messages=project_system_messages,
        seed=SEED,
    )

    write_to_md(name=PROJECT_ANALYSIS_MD, directory=REVIEWER_DIR_IN_PROJECT, data=project_analysis_result)
    logger.info(f'Done')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="This is an example of an AI assistant for project code review.")
    parser.add_argument(
        "-k",
        "--key",
        help="Your unique OpenAI API key for authentication",
        type=str,
        default=None
    )
    parser.add_argument(
        "-d",
        "--directory",
        help="The target directory where the script will be executed",
        type=str,
        default=__project_path__,
    )
    parser.add_argument(
        "-i",
        "--ignore_equals",
        help="Add directories or file to be completely ignored, separated by spaces "
             "(default: 'venv', '__pycache__', 'logs', reviewer folder name, reviewer dir in project (.reviewer'))",
        nargs="+",
        default=[]
    )
    parser.add_argument(
        "-is",
        "--ignore_starts_with",
        help="Add ignore files starting with these prefixes, separated by spaces (default: '.')",
        nargs="+",
        default=[]
    )
    parser.add_argument(
        "-ie",
        "--ignore_ends_with",
        help="Add ignore files ending with these extensions, separated by spaces (default: '.ipynb', '.md', '.log', '.lock')",
        nargs="+",
        default=[]
    )
    args = parser.parse_args()

    REVIEWER_DIR_IN_PROJECT = args.directory + '/' + REVIEWER_DIR_IN_PROJECT

    IGNORE_EQUALS += list(args.ignore_equals)
    IGNORE_STARTS_WITH += list(args.ignore_starts_with)
    IGNORE_ENDS_WITH += list(args.ignore_ends_with)

    if args.key:
        _client = get_openai_client(key=args.key)
    else:
        _client = get_openai_client()
    clear_dir(directory=REVIEWER_DIR_IN_PROJECT)

    logger = get_logger(formatter='%(asctime)s - %(name)s:%(lineno)s - %(levelname)s - %(message)s')

    asyncio.run(main(
        client=_client,
        directory=args.directory
    ))
