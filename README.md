## AICodeReviewer

This is an example of an AI assistant for project code review.

### Setup

To install the required packages, run the following command in your terminal:

```bash
pip install -r requirements.txt
```

### Parameters:

- `--key <API_KEY>`
    - Short: `-k`
    - Description: Your unique OpenAI API key for authentication.
    - Required: No
    - Note: If not specified, it is taken from the environment variable `OPENAI_API_KEY`
- `--directory <PROJECT_DIRECTORY>`
    - Short: `-d`
    - Description: The target directory where the script will be executed.
    - Required: No
    - Default: `__project_path__ = pathlib.Path(reviewer.py).parent.parent.resolve()`
- `--ignore_equals <IGNORED_NAMES>`
    - Short: `-i`
    - Description: Add directories or file to be completely ignored, separated by spaces.
    - Required: No
    - Default: `['venv', '__pycache__', 'logs', AICodeReviewer, .reviewer]`
- `--ignore_starts_with <FILE_PREFIXES>`
    - Short: `is`
    - Description: Add ignore files starting with these prefixes, separated by spaces.
    - Required: No
    - Default: `['.']`
- `--ignore_ends_with <FILE_EXTENSIONS>`
    - Short: `-ie`
    - Description: Add ignore files ending with these extensions, separated by spaces.
    - Required: No
    - Default: `['.ipynb', '.md', '.log', '.lock']`

### Run

#### Examples:
```python reviewer.py --key <API_KEY> --directory <PROJECT_DIRECTORY> --ignore_equals <IGNORED_NAMES> --ignore_ends_with <FILE_EXTENSIONS> --ignore_starts_with <FILE_PREFIXES>```

```python reviewer.py -k <API_KEY> -d <PROJECT_DIRECTORY> -i <IGNORED_NAMES> -ie <FILE_EXTENSIONS>```

#### If the AICodeReviewer folder is located in the project root:
```python -m AICodeReviewer.reviewer```

### Output
Creates a `.reviewer` folder in the directory of the project being analyzed.

Generates three files in `.reviewer` folder: `detail_analysis.md`, `short_analysis.md`, `project_analysis.md`.
- `detail_analysis.md` **Intermediate stage**
- `short_analysis.md` **Intermediate stage**
- `project_analysis.md`. **Result**


