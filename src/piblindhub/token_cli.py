"""Generate a high-entropy API token and the only value stored by the server."""

import argparse
import json
import secrets
from hashlib import sha256


def generate_token() -> dict[str, str]:
    token = secrets.token_urlsafe(32)
    return {
        "token": token,
        "sha256": sha256(token.encode("utf-8")).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a PiBlindHub API bearer token")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()
    generated = generate_token()
    if args.json:
        print(json.dumps(generated))
        return
    print("API token (shown once): {}".format(generated["token"]))
    print("PIBLINDHUB_API_TOKEN_SHA256={}".format(generated["sha256"]))


if __name__ == "__main__":
    main()
