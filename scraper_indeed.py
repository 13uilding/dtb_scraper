import requests
from bs4 import BeautifulSoup
import sys
import re
import os
import uuid
from azure.cosmos import exceptions, CosmosClient, PartitionKey
from dotenv import load_dotenv

filename = "indeed_results.html"
original = sys.stdout

load_dotenv()

# Dissecting the url |
BASE_URL_INDEED = 'https://www.indeed.com/jobs'
# TODO figure this stuff out a bit more later
query_strings = {
    'q': 'software%20developer%20%24110%2C000',
    'l': 'remote',  # location
    'fromage': '1',  # last 24 hours
    'vjk': 'f6590822192c4322',  # ??
    # Remote -- FIELD CHANGED TO 0kf%3Aattr(DSQF7)explvl(MID_LEVEL)%3B | SEEMS TO BE THE MOST IMPORTANT
    'sc': '0kf%3Aattr(DSQF7)%3B',
    'rbl': 'Remote',  # Another remote?
    'jlid': 'aaa2b906602aa8f5'
}
# indeed_sde_remote_24_remote_midLevel_110_remote_spring
indeed_spring = 'https://www.indeed.com/jobs?q=software%20developer%20%24110%2C000&l=remote&sc=0kf%3Aattr(DSQF7)attr(XH9RQ)explvl(MID_LEVEL)%3B&rbl=Remote&jlid=aaa2b906602aa8f5&fromage=1&vjk=578503532cfd08f4'
indeed_python = 'https://www.indeed.com/jobs?q=software%20developer%20%24110%2C000&l=remote&sc=0kf%3Aattr(DSQF7)attr(X62BT)explvl(MID_LEVEL)%3B&rbl=Remote&jlid=aaa2b906602aa8f5&fromage=1&vjk=646d639a763595fd'
indeed_react = 'https://www.indeed.com/jobs?q=software%20developer%20%24110%2C000&l=remote&sc=0kf%3Aattr(84K74)attr(DSQF7)explvl(MID_LEVEL)%3B&rbl=Remote&jlid=aaa2b906602aa8f5&fromage=1&vjk=67b654b9b4a3b396'
indeed_remote_js = 'https://www.indeed.com/jobs?q=software%20developer%20%24110%2C000&l=remote&sc=0kf%3Aattr(DSQF7)attr(JB2WC)explvl(MID_LEVEL)%3B&rbl=Remote&jlid=aaa2b906602aa8f5&fromage=1&vjk=67b654b9b4a3b396'

# Make this more generic in the future


class IndeedJobCard():
    def __init__(self, id, title, company, location, attributes, descriptions):
        self.id = id
        self.site = "indeed"
        self.title = title
        self.company = company
        self.location = location
        self.attributes = attributes
        self.descriptions = descriptions
        self.url = "https://www.indeed.com/viewjob?jk=" + id

    def __repr__(self):
        return str(self.__dict__)

    def __str__(self):
        return str(self.__dict__)


def getIndeedJobsSinceYesterday():
    page = requests.get(indeed_spring)

    soup = BeautifulSoup(page.content, "html.parser")
    # results = soup.find(id="mosaic-provider-jobcards")
    # ACTUALLY PRINTING STUFF I WANT
    card_pattern = re.compile("cardOutline tapItem fs-unmask result")
    salary_pattern = re.compile("metadata salary-snippet-container")
    # CARD ELEMENTS
    card_elements = soup.find_all(
        "div", class_=card_pattern)
    # print(card_elements[0].prettify())
    # This id seems useful: 578503532cfd08f4
    jobs = []
    # TO GET THE JOB ID
    for i in range(len(card_elements)):
        for cn in card_elements[i]['class']:
            if cn[:4] == "job_":
                id = cn[4:]
                title = card_elements[i].find(id=f"jobTitle-{id}").text
                company = card_elements[i].find(
                    "span", class_="companyName").text
                location = card_elements[i].find(
                    "div", class_="companyLocation").find("span").text
                # Typically contains pay, contract, hours
                attributes = [attribute_element.text for attribute_element in card_elements[i].find_all(
                    "div", class_="attribute_snippet")]
                # description list
                descriptions = [description_element.text for description_element in card_elements[i].find(
                    "div", class_="job-snippet").find_all("li")]
                jobs.append(IndeedJobCard(id, title, company,
                            location, attributes, descriptions))
    return jobs


def connectToCosmos():
    # Connect to cosmos db
    # TODO
    endpoint = os.getenv('cosmos_endpoint')
    key = os.getenv('cosmos_key')
    client = CosmosClient(endpoint, key)
    # Database
    database_name = 'linkedin'
    database = client.create_database_if_not_exists(id=database_name)
    # Container
    container_name = 'messages'
    container = database.create_container_if_not_exists(
        id=container_name,
        partition_key=PartitionKey(path="/site")
    )
    return client, database, container


def main():
    # Get jobs from Indeed
    jobs = getIndeedJobsSinceYesterday()
    # Connect to cosmos db and return client, database, container
    client, database, container = connectToCosmos()
    # Loop through retrieved jobs and insert into cosmos
    for job in jobs:
        container.create_item(body=job.__dict__)
        print("Inserted job: " + job.title)


if __name__ == "__main__":
    main()
    exit(0)
