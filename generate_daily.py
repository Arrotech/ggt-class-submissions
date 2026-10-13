#!/usr/bin/env python3
"""Create local blank templates; run ``uvicorn app:app`` for the web workflow."""

from sql_power_hour.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
