"""
Base functionalities to access pco and send mails
"""

from datetime import datetime, timezone, timedelta
from functools import lru_cache
import html
import json
import logging
import re
import urllib.request
from jinja2 import Template
from requests.auth import HTTPBasicAuth
import css_inline
import pytz
import requests
import yagmail


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


class PCO:
    """
    Class to connect to PCO
    """

    def __init__(self, app_id, token):
        self._pco_auth = HTTPBasicAuth(app_id, token)

    @lru_cache(maxsize=10000)
    def request(self, path: str):
        """
        Request information from PCO
        """
        if self._pco_auth is None:
            raise RuntimeError("PCO authentication is not established")
        if PCO_URL is None:
            raise RuntimeError("PCO url is not properly set")
        return _request_pco(self._pco_auth, path)

    @lru_cache(maxsize=1)
    def get_names(self):
        """
        Get names of the people in PCO
        """
        names = _get_names(self)

        teams = _get_teams(self)

        assignements = _get_assignements(self)

        for person_id, team_id in assignements:
            names[person_id]["teams"].append(teams[team_id])

        for name_id in names:
            logging.info("PCO:Person  %s", name_id)

        return names

    @lru_cache(maxsize=1)
    def get_plans(self):
        """
        Get information about the service plans
        """
        return _get_plans(self)

    @lru_cache(maxsize=100)
    def get_mail_address(self, person_id: str) -> str:
        """
        Get the mail address of a person
        """
        logging.info("PCO:Person:Mail  %s", person_id)
        return _get_mail_address(self, person_id)

    def get_band_leaders(self):
        """
        Get ids of the band leaders
        """
        return _get_band_leaders(self.get_names())

    def get_team_members(self, series_id: str, plan_id: str):
        """
        Get confirmed, pending and declined team members
        of a specific celebration
        """
        team_members = {}
        res = self.request(
            "/services/v2/series/"
            + series_id
            + "/plans/"
            + plan_id
            + "/team_members"
        )
        for person in res["data"]:
            person_id = person["relationships"]["person"]["data"]["id"]
            team_members[person_id] = {
                "name": person["attributes"]["name"],
                "position": [],
                "status": [],
            }
        for person in res["data"]:
            person_id = person["relationships"]["person"]["data"]["id"]
            team_members[person_id]["position"].append(
                person["attributes"]["team_position_name"]
            )
            team_members[person_id]["status"].append(
                person["attributes"]["status"]
            )
        return team_members

    def get_confirmed_team_members(self, series_id: str, plan_id: str):
        """
        Get confirmed team members of a specific celebration
        """
        confirmed_team = {}
        team = self.get_team_members(series_id, plan_id)
        for person_id, person in team.items():
            if "C" in person["status"]:
                confirmed_team[person_id] = person
        return confirmed_team

    def get_pending_team_members(self, series_id: str, plan_id: str):
        """
        Get pending team members of a specific celebration
        """
        pending_team = {}
        team = self.get_team_members(series_id, plan_id)
        for person_id, person in team.items():
            if "P" in person["status"]:
                pending_team[person_id] = person
        return pending_team


class Mail:
    """
    Wrapper for yag integration
    """

    def __init__(self, from_name: str, mail: str):
        self.name = from_name
        self.mail = mail
        self.yag = None
        self.dry_run = False

    def set_dry_run(self, is_dry_run: bool):
        """
        Do not send any mails if set to true
        """
        self.dry_run = is_dry_run

    def establish_connection(self, app_pw: str):
        """
        Connect to gmail
        """
        self.yag = yagmail.SMTP({self.mail: self.name}, app_pw)

    def send(self, to, subject, contents):
        """
        Wrap yag send function
        """
        self._log_send(to, subject, contents)
        if not self.dry_run:
            if self.yag is not None:
                self.yag.send(to=to, subject=subject, contents=contents)
            else:
                logging.error(
                    "Yag:Send:Mail  Establish connection with gmail first"
                )

    def send_votd(self, pco: PCO) -> int:
        """
        send mails to all #votd accounts
        """
        send_messages = 0
        for person_id, person in pco.get_names().items():
            if person["votd"]:
                ref, content = _get_votd_html_mail(person["first_name"])
                recipient = [pco.get_mail_address(person_id)]
                self.send(
                    to=recipient,
                    subject="Verse of the Day - " + ref,
                    contents=[content],
                )
                send_messages += 1
        return send_messages

    def send_celebration_reminder(self, pco: PCO) -> int:
        """
        send reminder mails for upcoming celebrations
        """
        send_mails = 0
        plans = pco.get_plans()

        start_reminder = (
            datetime.now(tz=pytz.UTC) + timedelta(weeks=2) - timedelta(days=1)
        )
        end_reminder = (
            datetime.now(tz=pytz.UTC) + timedelta(weeks=3) + timedelta(days=1)
        )

        for plan_id, plan in plans.items():
            if plan["date"] > start_reminder and plan["date"] < end_reminder:
                team_members = pco.get_confirmed_team_members(
                    plan["series_id"], plan_id
                )
                for person_id, team_person in team_members.items():
                    person = _get_names(pco)[person_id]
                    positions = ", ".join(team_person["position"])
                    plan_date = plan["date"].strftime("%d.%m.%Y")
                    content = _get_reminder_html_mail(
                        name=person["first_name"],
                        date=plan_date,
                        team_position=positions,
                        series_title=plan["series"],
                        plan_title=plan["plan"],
                        art_link=plan["artwork"],
                        pco_link=plan["pco_link"],
                    )
                    recipient = [pco.get_mail_address(person_id)]
                    self.send(
                        to=recipient,
                        subject=positions + " am " + plan_date,
                        contents=[content],
                    )
                    send_mails += 1
        return send_mails

    def _log_send(self, to, subject, contents):
        """
        Function stub to test functionalities
        """
        chars = 0
        for content in contents:
            chars += len(content)

        if self.dry_run:
            dry_run_text = "--dry-run  "
        else:
            dry_run_text = ""

        message = (
            "Yag:Send:Mail  "
            + dry_run_text
            + str(to)
            + " '"
            + str(subject)
            + "' "
            + str(len(contents))
            + " contents with "
            + str(chars)
            + " chars"
        )
        logging.info(message)


def _preheaderize(text: str) -> str:
    conversion_map = {
        ord("ß"): "ss",
        ord("ä"): "ae",
        ord("ö"): "oe",
        ord("ü"): "ue",
    }
    untagged = re.sub("<[^<]+?>", "", text)
    unescaped = html.unescape(untagged)
    noumlaut = unescaped.translate(conversion_map)
    alnumdot = re.sub(r"[^a-zA-Z0-9\s\.\,\!\:]+", "", noumlaut)
    return alnumdot


def _get_reminder_html_mail(
    name, date, team_position, series_title, art_link, plan_title, pco_link
):
    """
    get html content to send via mail
    """
    reminder_template_file = "assets/reminder_template.html"

    with open(reminder_template_file, encoding="utf-8") as file:
        template_text = file.read()

    template = Template(template_text)
    mail_content = template.render(
        preheader=_preheaderize(
            team_position + " am " + date + " Thema: " + plan_title
        ),
        name=name,
        date=date,
        team=team_position,
        series=series_title,
        art=art_link,
        plan=plan_title,
        link=pco_link,
    )
    inliner = css_inline.CSSInliner()
    inlined_content = inliner.inline(mail_content)
    entities_content = (
        inlined_content.encode("ascii", "xmlcharrefreplace")
        .decode("utf-8")
        .replace("\n", "")
    )
    return entities_content


def _get_votd_html_mail(name):
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
        preheader=_preheaderize(verse["text"]),
        verse=verse["text"],
        location=verse["ref"],
        link=verse["link"],
    )
    inliner = css_inline.CSSInliner()
    inlined_content = inliner.inline(mail_content)
    entities_content = (
        inlined_content.encode("ascii", "xmlcharrefreplace")
        .decode("utf-8")
        .replace("\n", "")
    )
    return verse["ref"], entities_content


def _request_pco(auth, path: str):
    response = requests.get(PCO_URL + path, auth=auth, timeout=1000)
    return json.loads(response.text)


def _get_mail_address(pco: PCO, person_id: str):
    res = pco.request("/people/v2/people/" + person_id + "/emails")
    for nested_mail in res["data"]:
        mail = nested_mail["attributes"]["address"]
    return mail


def _get_names(pco: PCO) -> dict:
    names = {}
    res = pco.request("/services/v2/people?per_page=200")
    for nested_array in res["data"]:
        identifier = nested_array["id"]
        name = nested_array["attributes"]["full_name"]
        first_name = nested_array["attributes"]["first_name"]
        notes = nested_array["attributes"]["notes"]

        is_votd = False

        if notes is not None:
            if "#votd" in notes:
                is_votd = True

        names[identifier] = {
            "name": name,
            "first_name": first_name,
            "votd": is_votd,
            "teams": [],
        }
    return names


def _get_teams(pco: PCO) -> dict:
    teams = {}
    res = pco.request("/services/v2/teams?include=team_positions&per_page=500")
    for nested_array in res["included"]:
        identifier = nested_array["id"]
        teams[identifier] = nested_array["attributes"]["name"]
    return teams


def _get_assignements(pco: PCO) -> list:
    assignements = []
    res = pco.request(
        "/services/v2/teams?per_page=500"
        + "&include=person_team_position_assignments"
    )
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


def _get_plans(pco: PCO) -> dict:
    plans = {}
    res = pco.request("/services/v2/series?per_page=100")
    for nested_array in res["data"]:
        identifier = nested_array["id"]
        series_title = nested_array["attributes"]["title"]
        series_artwork = nested_array["attributes"]["artwork_original"]
        res = pco.request(
            "/services/v2/series/" + nested_array["id"] + "/plans"
        )
        for nested_plan in res["data"]:
            plan_id = nested_plan["id"]
            plan_title = nested_plan["attributes"]["title"]
            plan_date = nested_plan["attributes"]["sort_date"]
            plan_date = datetime.fromisoformat(plan_date[:-1]).astimezone(
                timezone.utc
            )
            pco_link = nested_plan["attributes"]["planning_center_url"]

            plans[plan_id] = {
                "series_id": identifier,
                "series": series_title,
                "artwork": series_artwork,
                "date": plan_date,
                "plan": plan_title,
                "pco_link": pco_link,
            }
            logging.info(
                "PCO:Plan  %s,  %s,  %s", series_title, plan_title, plan_date
            )
    return plans
