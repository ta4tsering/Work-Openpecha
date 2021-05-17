import csv
import git 
import requests
import logging
import os
import re
import shutil
import uuid
import yaml
import time
import subprocess
from git import Repo 
from github import Github 
from pathlib import Path 


config = {
    "OP_ORG": "https://github.com/Openpecha"
}


logging.basicConfig(
    filename="layers_capitalized.log",
    format="%(levelname)s: %(message)s",
    level=logging.INFO,
)


def clean_dir(layers_output_dir):
    if layers_output_dir.is_dir():
            shutil.rmtree(str(layers_output_dir))


def notifier(msg):
    logging.info(msg)


def commit(repo, message, not_includes=[], branch="master"):
    has_changed = False

    for fn in repo.untracked_files:
        ignored = False
        for not_include_fn in not_includes:
            if not_include_fn in fn:
                ignored = True
        if ignored:
            continue
        if fn:
            repo.git.add(fn)
        if has_changed is False:
            has_changed = True

    if repo.is_dirty() is True:
        for fn in repo.git.diff(None, name_only=True).split("\n"):
            if fn:
                repo.git.add(fn)
            if has_changed is False:
                has_changed = True
        if has_changed is True:
            if not message:
                message = "Initial commit"
            repo.git.commit("-m", message)
            repo.git.push("origin", branch)
            notifier(f'{pecha_id} pagination Capitalized')
            print(f"{pecha_id} pagination Capitalized")
            
def write_to_file(pagination, file_path, file_list, new_file, vol_num):
    if pagination:
            content_yml = yaml.safe_dump(pagination, default_flow_style=False, sort_keys=False,  allow_unicode=True)
            Path(f'{file_path}').write_text(content_yml, encoding='utf-8')
            subprocess.run(f'cd ./{pecha_id}/{pecha_id}.opf/layers/v{vol_num:03};git mv {file_list} {new_file}', shell=True)
            print(f"{pecha_id}'s {file_list} renamed")
            change = True
    return change

def get_new_layers(pagination_content, num):
    if num == 1:
        pagination_content['annotation_type'] = "BookTitle"
        new_file = "BookTitle.yml"
    elif num == 2:
        pagination_content['annotation_type'] = "SubTitle"
        new_file = "SubTitle.yml"
    elif num == 3:
        pagination_content['annotation_type'] = "BookNumber"
        new_file =  "BookNumber.yml"
    elif num == 4:
        pagination_content['annotation_type'] = "PotiTitle"
        new_file = "PotiTitle.yml"
    elif num == 5:
        pagination_content['annotation_type'] = "Author"
        new_file =  "Author.yml"
    elif num == 6:
        pagination_content['annotation_type'] = "Chapter"
        new_file = "Chapter.yml"
    elif num == 7:
        pagination_content['annotation_type'] = "Text"
        new_file = "Text.yml"
    elif num == 8:
        pagination_content['annotation_type'] = "SubText"
        new_file = "SubText.yml"
    elif num == 9:
        pagination_content['annotation_type'] = "Pagination"
        new_file = "Pagination.yml"
    elif num == 10:
        pagination_content['annotation_type'] = "Citation"
        new_file = "Citation.yml"
    elif num == 11:
        pagination_content['annotation_type'] = "Correction"
        new_file = "Correction.yml"
    elif num == 12:
        pagination_content['annotation_type'] = "ErrorCandidate"
        new_file =  "ErrorCandidate.yml"
    elif num == 13:
        pagination_content['annotation_type'] = "Peydurma"
        new_file = "Peydurma.yml"
    elif num == 14:
        pagination_content['annotation_type'] = "Tsawa"
        new_file = "Sabche.yml"
    elif num == 15:
        pagination_content['annotation_type'] = "Tsawa"
        new_file = "Tsawa.yml"
    elif num == 16:
        pagination_content['annotation_type'] = "Tsawa"
        new_file = "Yigchung.yml"
    elif num == 17:
        pagination_content['annotation_type'] = "Archaic"
        new_file = "Archaic.yml"
    elif num == 18:
        pagination_content['annotation_type'] = "Durchen"
        new_file =  "Durchen.yml"
    elif num == 19:
        pagination_content['annotation_type'] = "Footnote"
        new_file =  "Footnote.yml"
    elif num == 20:
        pagination_content['annotation_type'] = "Tsawa"
        new_file = "Quotation.yml"
    return pagination_content, new_file

    


def file_name_change(content_file, pecha_id, vol_num, repo):
    num = 0
    pagination_path = content_file.path
    file_lists = ["book_title.yml","author.yml","chapter_title.yml","citation.yml""peydurma.yml","sabche.yml","yigchung.yml"]
    for file_list in file_lists:
        num += 1
        file_path = f"./{pecha_id}/{pecha_id}.opf/layers/v{vol_num:03}/{file_list}"
        if os.path.isfile(f"{file_path}"):
            pagination_content = repo.get_contents(f"./{pagination_path}/{file_list}")
            pagination_content = pagination_content.decoded_content.decode()
            pagination_content = yaml.safe_load(pagination_content)
            pagination, new_file = get_new_layers(pagination_content, num)
            change = write_to_file(pagination, file_path, file_list, new_file, vol_num)
    return change


def change_paginations(g, pecha_id):
    chnage = False
    vol_num = 0
    repo = g.get_repo(f"Openpecha/{pecha_id}")
    contents = repo.get_contents(f"./{pecha_id}.opf/layers")
    for content_file in contents:
        vol_num += 1
        change = file_name_change(content_file, pecha_id, vol_num, repo)     
    return change

def get_branch(repo, branch):
    if branch in repo.heads:
        return branch
    return "master"


def download_pecha(pecha_id, out_path=None, branch="master"):
    pecha_url = f"{config['OP_ORG']}/{pecha_id}.git"
    out_path = Path(out_path)
    out_path.mkdir(exist_ok=True, parents=True)
    pecha_path = out_path / pecha_id
    Repo.clone_from(pecha_url, str(pecha_path))
    repo = Repo(str(pecha_path))
    branch_to_pull = get_branch(repo, branch)
    repo.git.checkout(branch_to_pull)
    print(f"{pecha_id} Downloaded ")
    return pecha_path        


def setup_auth(repo, org, token):
    remote_url = repo.remote().url
    old_url = remote_url.split("//")
    authed_remote_url = f"{old_url[0]}//{org}:{token}@{old_url[1]}"
    repo.remote().set_url(authed_remote_url)

if __name__=='__main__':
    token = ""
    g = Github(token) 
    commit_msg = "layers filename capitalized"
    with open("catalog.csv", newline="") as csvfile:
        pechas = list(csv.reader(csvfile, delimiter=","))
        for pecha in pechas[101:276]:
            pecha_id = re.search("\[.+\]", pecha[0])[0][1:-1]
            file_path = './'
            pecha_path = download_pecha(pecha_id, file_path)
            change = change_paginations(g, pecha_id)
            if change == True:
                repo = Repo(pecha_path)
                setup_auth(repo, "Openpecha", token)
                commit(repo,commit_msg, branch="master")
                clean_dir(pecha_path)
                
