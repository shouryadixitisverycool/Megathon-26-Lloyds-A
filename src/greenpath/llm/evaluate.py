"""Write the offline adversarial report: python -m greenpath.llm.evaluate."""

from .evaluation import main


if __name__ == "__main__":
    raise SystemExit(main(default_output="reports/explanation_evaluation.json"))
