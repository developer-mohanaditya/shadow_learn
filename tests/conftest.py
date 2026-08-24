import os
import tempfile

os.environ["SHADOW_LEARN_DATA"] = tempfile.mkdtemp(prefix="shadow-learn-tests-")

