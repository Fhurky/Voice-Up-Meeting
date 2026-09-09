# Python artifact admission locks

`generator-linux-amd64-cp313-musllinux.requirements.lock` is an artifact admission record, not merely a
version constraint. It admits one binary wheel per pinned generator dependency for the default
Linux x86-64 / CPython 3.13 / musllinux matrix. `offline-bundle.sh` always invokes pip with
`--require-hashes`; a package mirror cannot replace an admitted wheel with different bytes under
the same name and version.

`build-system.requirements.lock` is the minimal subset used to build `kt-scaffold`. Its versions
must match `[build-system]` in `pyproject.toml`, and every entry and hash must also occur in the
generator lock. The build runs with `--no-isolation` in a disposable environment installed
offline from the already verified generator wheelhouse. This prevents PEP 517 from resolving a
second, unhashed copy of setuptools or wheel.

To admit an update in the connected artifact factory:

1. Update the complete version pins in `packaging/requirements.lock` and `pyproject.toml`.
2. Download only binary artifacts for the exact target tuple shown in the generator lock header.
3. Inspect and approve each resolved wheel, then record its `python -m pip hash <wheel>` SHA-256.
   Do not bulk-admit every wheel or sdist published for a version.
4. Update the generator and, where applicable, build-system locks. Run
   `pytest -q tests/test_packaging_python_hash_locks.py` before producing a bundle.

Another target tuple needs a separate reviewed generator hash lock. Supply its path through
`GENERATOR_REQUIREMENTS_LOCK` while setting the existing matrix variables; the default lock is
never silently reused across OS, architecture, Python version, or ABI. Keep matrices in separate
output directories.
