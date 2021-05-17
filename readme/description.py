import csv
import json
import logging
import re
import requests
import yaml
import emoji
import pyewts
from github import Github
from pathlib import Path
from rdflib import Graph
from rdflib.namespace import RDF, RDFS, SKOS, OWL, Namespace, NamespaceManager, XSD

BDR = Namespace("http://purl.bdrc.io/resource/")
BDO = Namespace("http://purl.bdrc.io/ontology/core/")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
EWTSCONV = pyewts.pyewts()

logging.basicConfig(
    filename="description_added.log",
    format="%(levelname)s: %(message)s",
    level=logging.INFO
)
def notifier(msg):
    logging.info(msg)

def get_title(meta):
    if meta['source_metadata']['title'] != None:
        title = meta['source_metadata']['title']
        return title
    else:
        return None

def ewtstobo(ewtsstr):
    res = EWTSCONV.toUnicode(ewtsstr)
    return res

def get_id(URI):    
    return URI.split("/")[-1]

def get_author_id(g, work_id):
    work_id = f"M{work_id}"
    instance_ids = g.objects(BDR[work_id], BDO["instanceOf"])
    for instance_id in instance_ids:
        instance_id = get_id(str(instance_id))
    agent_ids = g.objects(BDR[instance_id], BDO["creator"])
    for agent_id in agent_ids:
        agent_id = get_id(str(agent_id))
    author_ids = g.objects(BDR[agent_id], BDO["agent"])
    for author_id in author_ids:
        author_id = get_id(str(author_id))
    return author_id

def parse_author_ttl(author_ttl, work_id):
    g = Graph()
    try:
        g.parse(data=author_ttl, format="ttl")
    except:
        print(f"{work_id}.ttl Contains bad syntax")
        return {}
    author_id = get_author_id(g, work_id)
    author = g.value(BDR[author_id], SKOS["prefLabel"])
    author = ewtstobo(author)
    print(author)
    return author
   
def get_author_ttl(work_id):
    try:
        author_ttl = requests.get(f"http://purl.bdrc.io/query/graph/OP_info?R_RES=bdr:{work_id}&format=ttl")
        return author_ttl.text
    except:
        print(' TTL not Found!!!')
        return None

def get_work_id(meta):
    if meta['source_metadata']['id'] != None:
        work_id = meta['source_metadata']['id'][4:]
        return work_id
    else:
        return None

if __name__=="__main__":
    token = ""
    g = Github(token)
    headers = {"Authorization": f"bearer {token}"}
    # with open("catalog.csv", newline="") as csvfile:
    #     pechas = list(csv.reader(csvfile, delimiter=","))
    #     for pecha in pechas[278:]:
    #         pecha_id = re.search("\[.+\]", pecha[0])[0][1:-1]
    pecha_id = "P003000"
    repo = g.get_repo(f"Openpecha/{pecha_id}")
    contents = repo.get_contents(f"./{pecha_id}.opf/meta.yml")
    meta_content = contents.decoded_content.decode()
    meta_content = yaml.safe_load(meta_content)
    title = get_title(meta_content)
    work_id = get_work_id(meta_content)
    author_ttl = get_author_ttl(work_id)
    author = parse_author_ttl(author_ttl, work_id) 
    if author != None:
        data = {"description": f"{emoji.emojize(':blue_book:')}  {title}  {emoji.emojize(':writing_hand:')}  {author}  {emoji.emojize(':id:')}  BDRC:  {work_id}"}
    else:
        data = {"description": f"{emoji.emojize(':blue_book: ')}  {title}  {emoji.emojize(':id: ')}  BDRC:  { work_id}"}
    response = requests.patch(f"https://api.github.com/repos/ta4tsering/{pecha_id}", headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        notifier(f"{pecha_id} Description added successfully")
        print(f"{pecha_id} Description added successfully")
    else :
        notifier(f"{pecha_id} description not added due to status code {response.status_code}")
        print(f"{pecha_id} description not added due to status code {response.status_code}")

        # :blue_book: <title> <short title> <alternative title> :writing_hand: <author name> <alternative names> :id: <BDRC ID>, <Tsadra ID>, <other ID>