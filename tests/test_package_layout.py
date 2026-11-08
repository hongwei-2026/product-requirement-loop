from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_required_root_files_exist():
    for name in ("AGENTS.md", "README.md", "CHANGELOG.md", "pyproject.toml"):
        assert (ROOT / name).is_file(), name


def test_src_and_tests_dirs_exist():
    assert (ROOT / "src" / "product_requirement_loop" / "__init__.py").is_file()
    assert (ROOT / "tests").is_dir()


def test_package_version():
    from product_requirement_loop import __version__

    assert __version__
