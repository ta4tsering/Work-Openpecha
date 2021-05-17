import csv
import logging
import re
import yaml
from github import Github 
from pathlib import Path 


config = {
    "OP_ORG": "https://github.com/Openpecha"
}


logging.basicConfig(
    filename="pagination_imgnum.log",
    format="%(levelname)s: %(message)s",
    level=logging.INFO,
)

def notifier(msg):
    logging.info(msg)


def check_imgnum(pagination_content,pagination_path):
    changed = True
    paginations = pagination_content['annotations']
    for _num, uuid in enumerate(paginations,1):
        if 'imgnum' in paginations[uuid]:
            break
        else:
            changed = False
            break
    return changed
    

def get_pagination_content(content_file, pecha_id, repo):
    pagination_path = content_file.path
    pagination_content = repo.get_contents(f"./{pagination_path}/pagination.yml")
    pagination_content = pagination_content.decoded_content.decode()
    pagination_content = yaml.safe_load(pagination_content)
    changed = check_imgnum(pagination_content, pagination_path)
    if changed == False:
        return changed
    else:
        return True

def check_pagination(g, pecha_id):
    repo = g.get_repo(f"Openpecha/{pecha_id}")
    contents = repo.get_contents(f"./{pecha_id}.opf/layers")
    for content_file in contents:
        response = get_pagination_content(content_file, pecha_id, repo)
        if response == False:
            notifier(f"{pecha_id} needs imgnum update ")
            print(f"{pecha_id} needs imgnum update ")
            break
        else:
            print(f"{pecha_id} is updated")
    

if __name__=='__main__':
    token = ""
    g = Github(token) 
    commit_msg = "added imgnum to the pagination"
    with open("catalog.csv", newline="") as csvfile:
        pechas = list(csv.reader(csvfile, delimiter=","))
        for pecha in pechas[3626:4000]:
            pecha_id = re.search("\[.+\]", pecha[0])[0][1:-1]
            file_path = './'
            check_pagination(g, pecha_id)
    