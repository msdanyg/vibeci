# Root conftest.py — its mere presence makes pytest add the repo root to sys.path,
# so `import app...` / `import eval...` resolve whether the suite is invoked as
# `pytest` or `python -m pytest` (CI uses the former). Keep at the repo root.
