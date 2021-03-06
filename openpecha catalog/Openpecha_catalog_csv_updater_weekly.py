import re
import os
import requests
import json
import yaml
import logging
import csv
from git import Repo
from github import Github
from pathlib import Path

config = {
    "OP_ORG": "https://github.com/ta4tsering"
    }

def update_repo(g, commit_msg, new_content):
    try:
        repo = g.get_repo(f"ta4tsering/catalog")
        contents = repo.get_contents(f"./data/catalog.csv", ref="main")
        repo.update_file(contents.path, commit_msg , new_content, contents.sha, branch="main")
        print(f'catalog update completed..')
    except:
        print('Repo not found')


def write_new_catalog(repo_path, lines):
    first_row = f"ID,Title,Volume,Author,Source ID\n"
    with open(f"{repo_path}/data/catalog.csv", 'w') as csvfile:
        csvfile.write(first_row)
        writer = csv.writer(csvfile)    
        writer.writerows(lines)


def add_new_row_to_catalog(g, repo_path,repo_list):
    for pecha_id in repo_list:
        try:
            repo = g.get_repo(f"Openpecha/{pecha_id}")
            contents = repo.get_contents(f"{pecha_id}.opf/meta.yml")
            meta_content = contents.decoded_content.decode()
            metadata = yaml.safe_load(meta_content)
            work_id = metadata['source_metadata']['id'][4:]
            title = metadata['source_metadata']['title']
        except:
            work_id = None
            title = None
        if title == None:
            if work_id == None:
                row = f"[{pecha_id}](https://github.com/OpenPecha/{pecha_id}),,,,\n"
            else:
                row = f"[{pecha_id}](https://github.com/OpenPecha/{pecha_id}),,,,bdr:{work_id}\n"
        else:
            if work_id != None:
                row = f"[{pecha_id}](https://github.com/OpenPecha/{pecha_id}),{title},,,bdr:{work_id}\n"
            else: 
                row = f"[{pecha_id}](https://github.com/OpenPecha/{pecha_id}),{title},,,\n"
        with open(f"{repo_path}/data/catalog.csv", "a", encoding='utf-8') as csvfile:
            csvfile.write(row)


def add_only_repo_names_to_lines(repo_path, repo_names):
    lines = []
    repo_list = []
    key_list = []
    with open(f"{repo_path}/data/catalog.csv", newline="") as file:
        pechas = list(csv.reader(file, delimiter=","))
        for num, _ in repo_names.items():
            key_list.append(num)
        repo_key_list = sorted(key_list)
        print(repo_key_list)
        for key in repo_key_list:
            repo_name = repo_names[key]['repo']
            pecha_avail = False
            for pecha in pechas[1:]:
                res = not bool(pecha)
                row = pecha
                if res == False:
                    pecha_id = re.search("\[.+\]", pecha[0])[0][1:-1]
                    if pecha_id == repo_name:
                        lines.append(row)
                        print(f"{pecha_id} has repo")
                        pecha_avail = True
                        break
            if pecha_avail == False:
                print(f"{repo_name} repo is added to the catalog")
                repo_list.append(repo_name)
    return lines, repo_list


def get_repo_names(headers):
    repo_names = {}
    curr_name = {}
    new_name = 30000
    nums = 1
    for page_num in range(1,50):
        response = requests.get(f"https://api.github.com/orgs/Openpecha/repos?page={page_num}&per_page=100", headers=headers)
        data = response.json()
        for info in data:
            if type(info) is dict:
                repo_name = info["name"]
                if len(repo_name) == 32:
                    new_name += nums
                    name_key = new_name
                elif re.search(r"[catalog|hfml|users|ebook-template|nalanda-notes|diplomatic-kanjur]", repo_name):
                    continue
                elif len(repo_name) <= 7 :
                    name_key = repo_name[1:]
                    name_key = int(name_key)
                curr_name[name_key]={'repo':repo_name}
                repo_names.update(curr_name)
                curr_name = {}
    return repo_names

def get_branch(repo, branch):
    if branch in repo.heads:
        return branch
    return "master"

def download_repo(repo_name, out_path=None, branch="main"):
    pecha_url = f"{config['OP_ORG']}/{repo_name}.git"
    out_path = Path(out_path)
    out_path.mkdir(exist_ok=True, parents=True)
    repo_path = out_path / repo_name
    Repo.clone_from(pecha_url, str(repo_path))
    repo = Repo(str(repo_path))
    branch_to_pull = get_branch(repo, branch)
    repo.git.checkout(branch_to_pull)
    return repo_path        

if __name__ == '__main__':
    token = "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"
    g = Github(token)
    commit_msg = "updated catalog"
    headers = {"Authorization": f"bearer {token}"}
    file_path = './'
    repo_path = download_repo("catalog", file_path)
    repo_names = get_repo_names(headers)
    lines, repo_list = add_only_repo_names_to_lines(repo_path, repo_names)
    write_new_catalog(repo_path,lines)
    add_new_row_to_catalog(g,repo_path, repo_list)
    new_catalog = Path(f"{repo_path}/data/catalog.csv").read_text(encoding='utf-8')
    update_repo(g, commit_msg, new_catalog )
