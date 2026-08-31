from ._compat import load

_module = load("cli")
for _name in dir(_module):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_module, _name)


def main(argv=None):
    # Keep monkeypatches and callers using the installed module wired to the
    # implementation module used by the compatibility layout.
    _module.log_path = globals().get("log_path", _module.log_path)
    return _module.main(argv)
