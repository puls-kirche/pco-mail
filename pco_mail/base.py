"""
Base functionalities to access pco and send mails
"""

import logging
import json
import requests
import yagmail
from requests.auth import HTTPBasicAuth

# example constant variable
NAME = "pco_mail"
PCO_URL = "https://api.planningcenteronline.com"


def connect_mail(app_pw):
    """
    send mails via gmail
    """
    return yagmail.SMTP("puls.kirche", app_pw)


def _get_names(auth) -> dict:
    names = {}
    response = requests.get(
        PCO_URL + "/people/v2/people?per_page=200", auth=auth, timeout=1000
    )
    res = json.loads(response.text)
    for nested_array in res["data"]:
        identifier = nested_array["id"]
        name = nested_array["attributes"]["name"]

        response = requests.get(
            PCO_URL + "/people/v2/people/" + nested_array["id"] + "/emails",
            auth=auth,
            timeout=1000,
        )

        res = json.loads(response.text)
        for nested_mail in res["data"]:
            mail = nested_mail["attributes"]["address"]
        names[identifier] = {"name": name, "mail": mail, "teams": []}
        logging.info("Person  %s", identifier)
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
            logging.info("%s,  %s,  %s", series_title, plan_title, plan_date)
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
        logging.info("Band Leader: %s", names[person_id]["name"])

    plans = _get_plans(auth)

    return names, plans, band_leader_ids
