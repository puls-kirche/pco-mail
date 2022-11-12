"""
Base functionalities to access pco and send mails
"""

# import logging
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
    return yagmail.SMTP('puls.kirche', app_pw)


def access_pco(app_id, token):
    """
    access pco for testing
    """
    auth = HTTPBasicAuth(app_id, token)

    # response = requests.get(PCO_URL + "/services/v2/",
    #                         auth=auth, timeout=1000)

    # logging.info(response.status_code)
    # logging.debug(response.json())

    response = requests.get(PCO_URL + "/people/v2/people",
                            auth=auth, timeout=1000)

    name_list = []
    res = json.loads(response.text)
    for nested_array in res['data']:
        identifier = nested_array['id']
        name = nested_array['attributes']['name']

        response = requests.get(PCO_URL + "/people/v2/people/"
                                + nested_array['id'] + "/emails",
                                auth=auth, timeout=1000)

        res = json.loads(response.text)
        for nested_mail in res['data']:
            mail = nested_mail['attributes']['address']
        name_list.append({"person": [{"id": identifier},
                                     {"name": name},
                                     {"mail": mail},
                                     {"teams": "NA"}]})

    # print(name_list)

    plan_list = []
    response = requests.get(PCO_URL + "/services/v2/series",
                            auth=auth, timeout=1000)

    res = json.loads(response.text)
    for nested_array in res['data']:
        identifier = nested_array['id']
        series_title = nested_array['attributes']['title']
        response = requests.get(PCO_URL + "/services/v2/series/"
                                + nested_array['id'] + "/plans",
                                auth=auth, timeout=1000)

        res = json.loads(response.text)
        for nested_plan in res['data']:
            plan_id = nested_plan['id']
            plan_title = nested_plan['attributes']['title']
            plan_date = nested_plan['attributes']['sort_date']

            plan_list.append({"plan": [{"series_id": identifier},
                                       {"series": series_title},
                                       {"id": plan_id},
                                       {"date": plan_date},
                                       {"plan": plan_title}]})
            # print(series_title + ", " + plan_title + ", " + plan_date)

    # Show json
    # print(plan_list)

    # logging.info(response.status_code)
    # print(json.dumps(response.json()))

    return name_list, plan_list
