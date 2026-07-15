"""Module entrypoint for regenerating AuraSaaS mock data.

Supports:
    python -m app.scripts.generate_mock_data
"""

from scripts.generate_mock_data import init_mock_data


if __name__ == "__main__":
    init_mock_data(reset=True)
