import sys
import traceback

try:
    import evals.evaluate_retrieval
    evals.evaluate_retrieval.main()
except Exception as e:
    print("CRASH CAUGHT!")
    with open("crash.txt", "w") as f:
        f.write(traceback.format_exc())
