import pytest


def test_nlp_service_init():
    with pytest.raises(ModuleNotFoundError):
        import importlib
        import sys

        if "spacy" in sys.modules:
            del sys.modules["spacy"]

        import app.reports.ai.nlp as nlp_module
        importlib.reload(nlp_module)
        nlp_module.NLPService()._get_model()
