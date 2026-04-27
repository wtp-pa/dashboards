#!/usr/bin/env python3
"""
Fetch spending-by-department data from PA Treasury's OpenBookPA portal.

Source: https://www.patreasury.gov/openbookpa/

Output:
  data/spending-by-department.json — current FY expenditures per department

STATUS: stub. OpenBookPA may have hidden API endpoints behind its charts;
investigate before deciding scrape vs API.
"""

import sys


def main() -> int:
    print("[fetch_openbookpa] STUB — would fetch OpenBookPA data here")
    print("[fetch_openbookpa] No data written. Implementation pending.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
