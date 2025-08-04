import os
import re
import yaml
import json
import dotenv
import logging
import argparse
from loguru import logger
from datetime import datetime
from munch import DefaultMunch  # nested dict to object


class MyConfig(object):
    def __init__(self, *initial_data, **kwargs):
        for dictionary in initial_data:
            for key in dictionary:
                setattr(self, key, dictionary[key])
        for key in kwargs:
            setattr(self, key, kwargs[key])


def load_config(working_dir):
    config_path = os.path.join(working_dir, "config.yml")
    with open(config_path, 'rb') as fin:
        config_dict = yaml.load(fin, Loader=yaml.FullLoader)

    config_dict['working_dir'] = os.path.abspath(working_dir)
    result = DefaultMunch.fromDict(config_dict)
    return result


def set_log(log_path, log_level=logging.INFO):
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    # otherwise, run_gaia will produce messy logs

    logging.basicConfig(
        filename=log_path,
        level=log_level,
        format='[%(levelname)s][%(asctime)s.%(msecs)03d][%(process)d]'
               '[%(filename)s:%(lineno)d]: %(message)s',
        datefmt='(%Y-%m-%d) %H:%M:%S'
    )
    logging.getLogger("openai").setLevel(logging.ERROR)
    logging.getLogger("httpx").setLevel(logging.ERROR)
    logging.getLogger("pydantic").setLevel(logging.ERROR)


def set_loguru_log(log_path, log_level="INFO"):
    """
    Configure Loguru’s logger to write to a file and
    suppress noisy third-party logs.
    """
    # 1) Remove any pre-configured handlers
    logger.remove()

    # 2) Add a file handler
    #    – log_level can be any Loguru level name or integer
    #    – format mirrors your logging.basicConfig format
    logger.add(
        log_path,
        level=log_level,
        format=(
            "[<level>{level}</level>]"
            "[{time:YYYY-MM-DD HH:mm:ss.SSS}]"
            "[{process}]"
            "[{file.name}:{line}]: {message}"
        ),
        rotation=None,      # no rotation by default
        retention=None,     # keep all logs unless rotated
        enqueue=True,       # safe for multi-process
        serialize=False     # keep as human-readable
    )

    # 3) Silence overly-verbose libraries at ERROR level
    #    (they’ll still emit errors but not DEBUG/INFO)
    logger.disable("openai")
    logger.disable("httpx")
    logger.disable("pydantic")


def setup():
    dotenv.load_dotenv(dotenv_path='.env', override=True)

    parser = argparse.ArgumentParser()
    parser.add_argument('--working_dir', type=str, default='.',
                        help='path to configuration file')
    args, _ = parser.parse_known_args()  # <-- Ignore unrecognized arguments

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_filename = f"{timestamp}.log"
    log_path = os.path.join(args.working_dir, log_filename)
    set_log(log_path)

    config = load_config(args.working_dir)
    config.log_path = os.path.abspath(log_path)
    return config


# Escape unescaped interior double-quotes within JSON string literals so the text can be safely parsed
def sanitize_json(text):
    out, in_str, escape = [], False, False
    i, n = 0, len(text)
    # Sanitize JSON: escape interior double‑quotes and strip any backslash+'
    # so it becomes a literal single‑quote, preserving all other escapes.
    while i < n:
        ch = text[i]
        if not in_str:
            if ch == '"': in_str = True
            out.append(ch)

        else:
            if escape:
                out.append(ch)
                escape = False

            elif ch == '\\':
                # if next is a single‑quote, drop the backslash
                if i + 1 < n and text[i+1] == "'":
                    out.append("'")
                    i += 1
                else:
                    out.append(ch)
                    escape = True

            elif ch == '"':
                # lookahead for a true closer
                j = i + 1
                while j < n and text[j].isspace(): j += 1
                if j < n and text[j] in {':', ',', '}', ']'}:
                    out.append(ch)
                    in_str = False
                else:
                    out.append(r'\"')

            else:
                out.append(ch)

        i += 1

    return ''.join(out)


def _find_balanced_region(s: str, start: int):
    """Return (lo, hi) for the balanced JSON region starting at start, or None."""
    pair = {'{': '}', '[': ']'}
    opener = s[start]
    if opener not in pair:
        return None
    closer = pair[opener]
    stack = [closer]
    i = start + 1
    n = len(s)
    while i < n:
        ch = s[i]
        # IMPORTANT: do NOT try to track quotes here (pre-sanitization may be invalid).
        if ch in pair:                 # new nested object/array
            stack.append(pair[ch])
        elif ch in (']', '}'):         # possible close
            if not stack or ch != stack[-1]:
                return None            # mismatched -> not a valid JSON region
            stack.pop()
            if not stack:
                return (start, i + 1)  # inclusive end
        i += 1
    return None                        # ran out before closing


def _json_candidates(s: str):
    """Yield (lo, hi) spans for candidate JSON blocks in s."""
    pos = 0
    n = len(s)
    while pos < n:
        # next opening brace/bracket
        i1 = s.find('{', pos)
        i2 = s.find('[', pos)
        if i1 == -1 and i2 == -1:
            break
        start = i1 if i2 == -1 else (i2 if i1 == -1 else min(i1, i2))
        reg = _find_balanced_region(s, start)
        if reg:
            yield reg
        pos = start + 1


def extract_json_from_string(original_text: str):
    """
    1) Search raw text for the first balanced {...} or [...]
    2) Run sanitize_json on that candidate
    3) Try json.loads; if it fails, try the next candidate
    """
    text = original_text

    for lo, hi in _json_candidates(text):
        candidate = text[lo:hi]
        cleaned = sanitize_json(candidate)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logging.debug(f"Candidate at {lo}:{hi} failed JSON parse: {e}")

    # 3C) if we still failed…
    logging.error(f"No JSON data found. "
                  f"Original text:\n{original_text}")
    return {}


def extract_code_from_string(text, code_type):
    code = ""
    code_type_str = '```' + code_type.lower()
    if code_type_str in text:
        code = text.split(code_type_str)[1].split('```')[0]
    elif '```' in code:
        code = text.split('```')[1].split('```')[0]
    else:
        raise NotImplementedError
    return code.strip()
