"""
A simple utility to edit accounts.  Example usage:

    proxy-cli list           # List all accounts
    proxy-cli list -g cs324  # List accounts under the `cs324` group
    proxy-cli list -m gpt3   # Show quotas for the `gpt3` model group

    proxy-cli create                      # Create a new account
    proxy-cli create -e psl@stanford.edu  # Create a new account with extra information

    proxy-cli update -k ... -d "For robustness project"  # Set the description
    proxy-cli update -k ... -g cs324 test                # Set the groups
    proxy-cli update -k ... -q gpt3.daily=10000          # Set quota
    proxy-cli update --help                              # For information about all the fields
"""

import argparse
from typing import List, Dict
import re
import sys

from common.hierarchical_logger import hlog
from .remote_service import RemoteService, add_service_args, create_remote_service, create_authentication
from common.authentication import Authentication
from .accounts import Usage, Account

GRANULARITIES = ["daily", "monthly", "total"]


def render_usage(usage: Usage) -> str:
    """Renders a particular Usage (used/quota) as a string."""
    if usage.quota is not None:
        return f"{usage.used}/{usage.quota}"
    else:
        return f"{usage.used}"


def render_header(show_model_groups: List[str]) -> List[str]:
    """Return list of column headers related to an account."""
    header = ["api_key", "description", "emails", "groups", "is_admin"]
    for model_group in show_model_groups:
        for granularity in GRANULARITIES:
            header.append(f"{model_group}.{granularity}")
    return header


def render_account(account: Account) -> Dict[str, str]:
    result = {
        "api_key": account.api_key,
        "description": account.description,
        "emails": ",".join(account.emails),
        "groups": ",".join(account.groups),
        "is_admin": "admin" if account.is_admin else "-",
    }
    for model_group, usages in account.usages.items():
        for granularity in GRANULARITIES:
            result[f"{model_group}.{granularity}"] = render_usage(usages[granularity])
    return result


def print_table(header: List[str], items: List[Dict[str, str]]):
    """Print a table with `header`, and one row per item."""
    rows = [[item.get(key, "") for key in header] for item in items]
    widths = [max(len(row[i]) for row in [header] + rows) for i in range(len(header))]
    fmt_str = "".join("{:" + str(widths[i] + 2) + "}" for i in range(len(header)))
    for row in [header] + rows:
        hlog(fmt_str.format(*row))


def print_item(header: List[str], item: Dict[str, str]):
    # In the future, might want to print one line per item
    print_table(header, [item])


def do_list_command(service: RemoteService, auth: Authentication, args):
    header = render_header(args.show_model_groups)
    items = []
    for account in service.get_accounts(auth):
        # Filter by group
        if args.group is not None and args.group not in account.groups:
            continue

        items.append(render_account(account))
    print_table(header, items)


def do_create_update_command(service: RemoteService, auth: Authentication, args):
    if args.command == "create":
        account = service.create_account(auth)
    elif args.command == "update":
        # TODO: add additional arguments to `get_accounts` to select a single account based on api key
        accounts = [account for account in service.get_accounts(auth) if account.api_key == args.api_key]
        if len(accounts) == 0:
            hlog(f"No account found with API key {args.api_key}")
            sys.exit(1)
        else:
            assert len(accounts) == 1
            account = accounts[0]
    else:
        raise Exception(f"Invalid command: {args.command}")

    # Update fields
    if args.description is not None:
        account.description = args.description
    if args.emails is not None:
        account.emails = args.emails
    if args.groups is not None:
        account.groups = args.groups
    if args.is_admin is not None:
        account.is_admin = bool(args.is_admin)

    # Update quotas
    for quota_str in args.quotas:
        m = re.match("(\w+)\.(\w+)=(\d+)", quota_str)
        if not m:
            raise Exception(
                f"Invalid format: {quota_str}, expect <model_group>.<granularity>=<quota> (e.g., gpt3.daily=10000)"
            )
        model_group, granularity, quota = m.group(1), m.group(2), m.group(3)

        if model_group not in account.usages:
            usages = account.usages[model_group] = {}
        else:
            usages = account.usages[model_group]
        if granularity not in usages:
            usage = usages[granularity] = Usage()
        else:
            usage = usages[granularity]
        usage.quota = int(quota)

    # Commit changes
    account = service.update_account(auth, account)

    # Print out created/updated account information
    header = render_header(show_model_groups=list(account.usages.keys()))
    item = render_account(account)
    print_item(header, item)


def main():
    parser = argparse.ArgumentParser()
    add_service_args(parser)
    subparsers = parser.add_subparsers(dest="command")

    list_parser = subparsers.add_parser("list", help="List accounts")
    list_parser.add_argument("-g", "--group", help="List only accounts in this group")
    list_parser.add_argument(
        "-m", "--show-model-groups", nargs="*", help="Show usage for these model groups", default=[]
    )

    def add_account_arguments(parser):
        parser.add_argument(
            "-m", "--show-model-groups", nargs="*", help="Show usage for these model groups", default=[]
        )
        parser.add_argument("-d", "--description", help="List only accounts in this group")
        parser.add_argument("-e", "--emails", nargs="*", help="Use these emails")
        parser.add_argument("-g", "--groups", nargs="*", help="Use these groups")
        parser.add_argument("-a", "--is-admin", help="Specify whether account is an admin")
        parser.add_argument("-q", "--quotas", nargs="*", help="Set these quotas (gpt3:daily:20000)", default=[])

    create_parser = subparsers.add_parser("create", help="Create new account")
    add_account_arguments(create_parser)

    update_parser = subparsers.add_parser("update", help="Update an existing account")
    update_parser.add_argument(
        "-k", "--api-key", help="Update this account (update new account if not specified)", required=True
    )
    add_account_arguments(update_parser)

    args = parser.parse_args()

    service = create_remote_service(args)
    auth = create_authentication(args)

    if args.command == "list":
        do_list_command(service, auth, args)
    elif args.command == "create" or args.command == "update":
        do_create_update_command(service, auth, args)
    else:
        parser.print_help()
        sys.exit(1)
