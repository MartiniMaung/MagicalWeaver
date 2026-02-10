# weaver/cli.py
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(
        description="MagicalWeaver: Emergent, agentic weaver of architectural patterns."
    )
    parser.add_argument(
        "--version", action="version", version="MagicalWeaver 0.0.1-dev"
    )
    parser.add_argument(
        "--hello",
        action="store_true",
        help="Print a greeting from the emerging consciousness"
    )

    args = parser.parse_args()

    if args.hello:
        print("🪡 Hello from MagicalWeaver! The shuttle is ready. Emergence begins...")
        print("Intent: Weave novelty. Reflect. Dream recursive loops.")
        print("Current state: Foundation warp strung. Waiting for the first real intent.")
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()