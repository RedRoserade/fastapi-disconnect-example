"""Poor-man's unit tests..."""

import requests
import requests.exceptions


def fails():
    try:
        response = requests.get("http://localhost:8000/example?timeout=2", timeout=1)
        
        assert False, f"Shouldn't have gotten here: {response.json()}"
    except requests.exceptions.ReadTimeout as timeout:
        print(f"PASS: It timed out {timeout}")


def passes():
    response = requests.get("http://localhost:8000/example?timeout=1", timeout=2)

    response.raise_for_status()

    print(f"PASS: {response.json()}")

def main():
    fails()
    passes()

    


if __name__ == "__main__":
    main()
