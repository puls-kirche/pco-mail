"""CLI interface for pco_mail project.

Be creative! do whatever you want!

- Install click or typer and create a CLI app
- Use builtin argparse
- Start a web application
- Import things from your .base module
"""
import argparse
import logging
from .base import access_pco, connect_mail


def _parse_arguments():
    parser = argparse.ArgumentParser(
        prog="PCO Mail",
        description="Uses PCO to send invitations via mail",
        epilog="Made with ♥",
    )
    parser.add_argument("-t", "--pco-token")
    parser.add_argument("-a", "--pco-app-id")
    parser.add_argument("-g", "--gmail-app-pw")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


def _setup_logging(verbose: bool):
    if verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.ERROR)


def main():  # pragma: no cover
    """
    The main function executes on commands:
    `python -m pco_mail` and `$ pco_mail `.

    This is your program's entry point.

    You can change this function to do whatever you want.
    Examples:
        * Run a test suite
        * Run a server
        * Do some other stuff
        * Run a command line application (Click, Typer, ArgParse)
        * List all available tasks
        * Run an application (Flask, FastAPI, Django, etc.)
    """
    args = _parse_arguments()
    _setup_logging(args.verbose)

    names, plans, band_leader_ids = access_pco(args.pco_app_id, args.pco_token)

    print("Names: " + len(names))
    print("Plans: " + len(plans))

    yag = connect_mail(args.gmail_app_pw)

    contents = ['There are ', len(names),
                ' people and ', len(plans),
                ' plans.\nThe band leaders are:\n']

    for person_id in band_leader_ids:
        contents.append("- " + names[person_id]["name"] +
                        " (" + names[person_id]["mail"] + ")\n")

    yag.send('printed.robots@gmail.com', 'pco mail test',
             contents)
