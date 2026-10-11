"""Optional paid-provider entry point; requires CLI opt-in, credentials and prices."""

from greenr.llm.live_evaluation import main


if __name__ == "__main__":
    raise SystemExit(main())
