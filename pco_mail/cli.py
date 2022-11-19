"""
CLI interface for pco_mail project.
"""
import argparse
import logging
from .base import PCO, Mail


def _parse_arguments():
    parser = argparse.ArgumentParser(
        prog="PCO Mail",
        description="Uses PCO to send invitations via mail",
        epilog="Made for ✝ is ♥",
    )
    parser.add_argument(
        "-t",
        "--pco-token",
        help="This token is a secret that allows to access PCO",
    )
    parser.add_argument(
        "-a",
        "--pco-app-id",
        help="The 'APP Id' is the user name that is needed to access PCO",
    )
    parser.add_argument(
        "-g",
        "--gmail-app-pw",
        help="The GMail app password to access a gmail account",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Display verbose message. Do not activate in CI",
    )
    parser.add_argument(
        "--votd",
        action="store_true",
        help="Activate 'Verse-of-the-Day' messages for this run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run everything without sending mails. Instead log the messages",
    )
    return parser.parse_args()


def _setup_logging(verbose: bool):
    if verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)


# def test_main():
#     """
#     Test some stuff
#     """
#     from datetime import datetime
#     from ics import Calendar, Event

#     c = Calendar()
#     e = Event()
#     e.summary = "My cool event"
#     e.description = "A meaningful description"
#     e.begin = datetime.fromisoformat("2022-06-06T12:05:23+02:00")
#     e.end = datetime.fromisoformat("2022-06-06T13:05:23+02:00")
#     c.events.append(e)
#     c
# # [<Event 'My cool event' begin:2014-01-01 00:00:00 end:2014-01-01 00:00:01>]
#     with open("my.ics", "w") as my_file:
#         my_file.writelines(c.serialize_iter())
#     # and it's done !


def main():  # pragma: no cover
    """
    The main function. Use help to find out more:
    `python -m pco_mail -h` and `$ pco_mail -h`.
    """
    args = _parse_arguments()
    _setup_logging(args.verbose)

    pco = PCO(args.pco_app_id, args.pco_token)

    print("Names: ", len(pco.get_names()))
    # print("Plans: ", len(pco.get_plans()))
    print("Band Leaders: ", len(pco.get_band_leaders()))

    mail = Mail("PULS-Kirche-fuer-Schweinfurt", "puls.kirche@gmail.com")

    if args.dry_run:
        mail.set_dry_run(True)
    else:
        mail.establish_connection(args.gmail_app_pw)

    # https://github.com/leemunroe/responsive-html-email-template/blob/master/email-inlined.html

    if args.votd:
        send_messages = mail.send_votd(pco)
        print("Send " + str(send_messages) + " 'Verse of the Day' messages")
