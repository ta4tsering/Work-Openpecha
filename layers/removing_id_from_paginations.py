import csv
import git 
import logging
import os
import re
import shutil
import uuid
import yaml

from git import Repo 
from github import Github 
from pathlib import Path 


config = {
    "OP_ORG": "https://github.com/Openpecha"
}


logging.basicConfig(
    filename="pagination_updated.log",
    format="%(levelname)s: %(message)s",
    level=logging.INFO,
)


def clean_dir(layers_output_dir):
    if layers_output_dir.is_dir():
            shutil.rmtree(str(layers_output_dir))


def _mkdir(path):
    if path.is_dir():
        return path
    path.mkdir(exist_ok=True, parents=True)
    return path


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
            notifier(f"{pecha_id} pagination updated")
            print(f"{pecha_id} pagination updated")

def get_new_annotations(pagination_content,pagination_path):
    vol_num = Path(f"{pagination_path}").name
    new_pagination = {}
    pagination = {}
    paginations = pagination_content['annotations']
    if paginations != []:
        for pg_uuid, pg_info in enumerate(paginations,1):
            uid = pg_info['id']
            new_pagination[f"{uid}"] = { 
                'page_index': pg_info['page_index'],
                'page_info': pg_info['page_info'],
                'reference': pg_info['reference'],
                'span':{
                    'start': pg_info['span']['start'],
                    'end': pg_info['span']['end']
                }
            }
            pagination.update(new_pagination)
            new_pagination = {}
        return pagination, vol_num
    else:
        notifier( f'Pecha id :{pecha_id} vol_num:{vol_num} empty pagination')
        print( f'Pecha id :{pecha_id} vol_num:{vol_num} empty pagination')
        return None, vol_num


def get_pagination_content(g, content_file, pecha_id, repo):
    pagination_path = content_file.path
    pagination_content = repo.get_contents(f"./{pagination_path}/Pagination.yml")
    pagination_content = pagination_content.decoded_content.decode()
    pagination_content = yaml.safe_load(pagination_content)
    pagination, vol_num = get_new_annotations(pagination_content, pagination_path)
    if pagination != None:
        return pagination, pagination_content, pagination_path, vol_num
    else:
        return None, None, None, None

def get_new_layers(g, pecha_id):
    repo = g.get_repo(f"Openpecha/{pecha_id}")
    contents = repo.get_contents(f"./{pecha_id}.opf/layers")
    for content_file in contents:
        pagination, pagination_content, pagination_path, vol_num = get_pagination_content(g, content_file, pecha_id, repo)
        if pagination != None:
            del pagination_content['annotations']
            pagination_content[f'annotations'] = pagination
            content_yml = yaml.safe_dump(pagination_content, default_flow_style=False, sort_keys=False,  allow_unicode=True)
            Path(f"./{pecha_id}/{pecha_id}.opf/layers/{vol_num}/Pagination.yml").write_text(content_yml, encoding='utf-8')


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
    notifier(f"{pecha_id} Downloaded ")
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
    commit_msg = "pagination updated"
    # with open("catalog.csv", newline="") as csvfile:
    #     pechas = list(csv.reader(csvfile, delimiter=","))
    #     for pecha in pechas[4302:4303]:
    #         pecha_id = re.search("\[.+\]", pecha[0])[0][1:-1]
    pecha_id = 'P000010'
    file_path = './'
    pecha_path = download_pecha(pecha_id, file_path)
    get_new_layers(g, pecha_id)
    repo = Repo(pecha_path)
    setup_auth(repo, "Openpecha", token)
    commit(repo,commit_msg, branch="master")
    clean_dir(pecha_path)
