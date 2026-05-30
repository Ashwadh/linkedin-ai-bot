"""
test_run.py — One-time test script to run the full LinkedIn automation pipeline.
"""

from src.bot_logic import run_daily_automation

if __name__ == "__main__":
    result = run_daily_automation()
    print("\n--- FINAL RESULT ---")
    for key, value in result.items():
        print(f"  {key}: {value}")
