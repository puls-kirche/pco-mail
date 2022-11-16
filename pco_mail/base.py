"""
Base functionalities to access pco and send mails
"""

import json
import logging
import urllib.request
from functools import lru_cache
from requests.auth import HTTPBasicAuth
from jinja2 import Template
import requests
import yagmail
import css_inline


# example constant variable
NAME = "pco_mail"
PCO_URL = "https://api.planningcenteronline.com"
BIBLEGATEWAY = "https://www.biblegateway.com/votd/get/?format=json&version="


@lru_cache(maxsize=None)
def get_verse_of_the_day(translation: str = "NGU-DE") -> dict:
    """
    get verse of the day from biblegateway.com
    """

    with urllib.request.urlopen(BIBLEGATEWAY + translation) as url:
        verse_json = json.load(url)

    verse = {}
    verse["text"] = verse_json["votd"]["content"]
    verse["ref"] = verse_json["votd"]["display_ref"]
    verse["link"] = verse_json["votd"]["permalink"]

    return verse


def connect_mail(app_pw):
    """
    send mails via gmail
    """
    return yagmail.SMTP({"puls.kirche@gmail.com": "PULS Kirche"}, app_pw)


class MailStub:
    """
    Stub the yag
    """

    def send(self, to, subject, contents):
        """
        Function stub to test functionalities
        """
        message = (
            "Yag:Send:Mail  --dry-run  "
            + str(to)
            + " '"
            + str(subject)
            + "' "
            + str(contents)
        )
        logging.info(message)


def get_votd_html_mail(name):
    """
    get html content to send via mail
    """
    votd_template_file = "assets/votd_template.html"

    verse = get_verse_of_the_day()

    with open(votd_template_file, encoding="utf-8") as file:
        template_text = file.read()

    template = Template(template_text)
    mail_content = template.render(
        name=name,
        verse=verse["text"],
        location=verse["ref"],
        link=verse["link"],
    )
    inliner = css_inline.CSSInliner(remove_style_tags=True)
    inlined_content = inliner.inline(mail_content)
    entities_content = (
        inlined_content.encode("ascii", "xmlcharrefreplace")
        .decode("utf-8")
        .replace("\n", "")
    )
    return verse["ref"], entities_content


def send_votd(yag, names):
    """
    send mails to all #votd accounts
    """
    send_messages = 0
    for person in names.values():
        if person["votd"]:
            ref, html = get_votd_html_mail(person["first_name"])
            recipient = {person["mail"]: person["name"]}
            yag.send(
                to=recipient,
                subject="Verse of the Day - " + ref,
                contents=[html],
            )
            send_messages += 1
    print("Send " + str(send_messages) + " 'Verse of the Day' messages")


def _get_names(auth) -> dict:
    names = {}
    response = requests.get(
        PCO_URL + "/services/v2/people?per_page=200", auth=auth, timeout=1000
    )
    res = json.loads(response.text)
    for nested_array in res["data"]:
        identifier = nested_array["id"]
        name = nested_array["attributes"]["full_name"]
        first_name = nested_array["attributes"]["first_name"]
        notes = nested_array["attributes"]["notes"]

        is_votd = False

        if notes is not None:
            if "#votd" in notes:
                is_votd = True

        response = requests.get(
            PCO_URL + "/people/v2/people/" + nested_array["id"] + "/emails",
            auth=auth,
            timeout=1000,
        )

        res = json.loads(response.text)
        for nested_mail in res["data"]:
            mail = nested_mail["attributes"]["address"]
        names[identifier] = {
            "name": name,
            "first_name": first_name,
            "mail": mail,
            "votd": is_votd,
            "teams": [],
        }
        logging.info("PCO:Person  %s", identifier)
    return names


def _get_teams(auth) -> dict:
    teams = {}
    response = requests.get(
        PCO_URL
        + "/services/v2/teams"
        + "?include=team_positions&per_page=500",
        auth=auth,
        timeout=1000,
    )
    res = json.loads(response.text)
    for nested_array in res["included"]:
        identifier = nested_array["id"]
        teams[identifier] = nested_array["attributes"]["name"]
    return teams


def _get_assignements(auth) -> list:
    assignements = []
    response = requests.get(
        PCO_URL
        + "/services/v2/teams?per_page=500"
        + "&include=person_team_position_assignments",
        auth=auth,
        timeout=1000,
    )
    res = json.loads(response.text)
    for nested_array in res["included"]:
        person_id = nested_array["relationships"]["person"]["data"]["id"]
        team_id = nested_array["relationships"]["team_position"]["data"]["id"]
        assignements.append((person_id, team_id))
    return assignements


def _get_band_leaders(names: dict) -> list:
    band_leaders = []
    for person_id, person in names.items():
        if "Band Leader" in person["teams"]:
            band_leaders.append(person_id)
    return band_leaders


def _get_plans(auth) -> dict:
    plans = {}
    response = requests.get(
        PCO_URL + "/services/v2/series?per_page=100", auth=auth, timeout=1000
    )
    res = json.loads(response.text)
    for nested_array in res["data"]:
        identifier = nested_array["id"]
        series_title = nested_array["attributes"]["title"]
        response = requests.get(
            PCO_URL + "/services/v2/series/" + nested_array["id"] + "/plans",
            auth=auth,
            timeout=1000,
        )

        res = json.loads(response.text)
        for nested_plan in res["data"]:
            plan_id = nested_plan["id"]
            plan_title = nested_plan["attributes"]["title"]
            plan_date = nested_plan["attributes"]["sort_date"]

            plans[plan_id] = {
                "series_id": identifier,
                "series": series_title,
                "date": plan_date,
                "plan": plan_title,
            }
            logging.info(
                "PCO:Series  %s,  %s,  %s", series_title, plan_title, plan_date
            )
    return plans


def access_pco(app_id, token):
    """
    access pco for testing
    """
    auth = HTTPBasicAuth(app_id, token)

    names = _get_names(auth)

    teams = _get_teams(auth)

    assignements = _get_assignements(auth)

    for person_id, team_id in assignements:
        names[person_id]["teams"].append(teams[team_id])

    band_leader_ids = _get_band_leaders(names)

    for person_id in band_leader_ids:
        logging.info("PCO:BandLead  Band Leader: %s", names[person_id]["name"])

    plans = _get_plans(auth)

    return names, plans, band_leader_ids
