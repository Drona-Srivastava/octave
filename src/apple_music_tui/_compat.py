from importlib import util
from pathlib import Path
import sys


def load(name: str):
    module_name = f"apple_music_tui._flat_{name}"
    source = Path(__file__).resolve().parents[1] / f"{name}.py"
    spec = util.spec_from_file_location(module_name, source)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load {source}")
    module = util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
