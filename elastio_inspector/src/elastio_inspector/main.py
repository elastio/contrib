import argparse

from elastio_inspector.handler import scan, scan_globals


def main():

    parser = argparse.ArgumentParser(
        description="Elastio Inspector for AWS",
    )
    parser.add_argument(
        "-d",
        "--destroy",
        action="store_true",
        default=False,
        help="Destroys ONLY Elastio Regional Resources",
    )
    parser.add_argument(
        "-g",
        "--globals",
        action="store_true",
        default=False,
        help="Include Global Resources for Scanning Only",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        default=False,
        help="Auto Approves Destruction of Regional Resources",
    )
    parser.add_argument(
        "--region", default="us-west-2", help="The REGION to scan (default: us-west-2)"
    )
    parser.add_argument("--vault", help="Limit the scan to a vault name")

    args = parser.parse_args()

    if args.auto_approve:
        print("Auto approve is not implemented. Proceeding without auto-approve")

    if args.destroy:
        print("Running in destruction mode.")

    scan(args, None)

    if args.globals:
        scan_globals(args, None)


if __name__ == "__main__":
    main()
