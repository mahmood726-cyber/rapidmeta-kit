import os
import sys

import pytest

# Make `import rmharness` work when pytest is run from the harness/ directory.
HARNESS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HARNESS)
KIT = os.path.dirname(HARNESS)

BUNDLE_DIR = os.path.join(KIT, "bundle-example", "finerenone_ckd")


@pytest.fixture
def built_bundle():
    """The committed example bundle, as (loaded dict, bundle_dir)."""
    from rmharness import bundle as _bundle
    path = os.path.join(BUNDLE_DIR, "bundle.json")
    return _bundle.load(path), BUNDLE_DIR
