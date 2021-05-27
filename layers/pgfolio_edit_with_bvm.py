import csv
import git 
import logging
import os
import re
import shutil
import requests
import yaml

from git import Repo 
from github import Github 
from pathlib import Path 


config = {
    "OP_ORG": "https://github.com/ta4tsering"
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


def commit(repo, message, not_includes=[], branch="main"):
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
            notifier(f"{pecha_id} layers file's id removed")
            print(f"{pecha_id} layers file's id removed")


def write_to_file(pecha_id, pagination_content, annotations, image_group, vol_num):
    change = False
    if annotations:
        del pagination_content['annotations']
        pagination_content['image_group_id'] = image_group
        pagination_content[f'annotations'] = annotations
        content_yml = yaml.safe_dump(pagination_content, default_flow_style=False, sort_keys=False,  allow_unicode=True)
        Path(f'./{pecha_id}/{pecha_id}.opf/layers/{vol_num}/Pagination.yml').write_text(content_yml, encoding='utf-8')
        change = True
    return change


def get_new_annotations(pagination_content, pagination_infos):
    annotations = pagination_content['annotations']
    if annotations != []:
        for info_num in pagination_infos:
            for uid in annotations:
                if pagination_infos[info_num]['filename'] == annotations[uid]['reference']:
                    pagination = pagination_infos[info_num]['pagination']
                    annotations[uid]['pagination'] = pagination
                    break
    return annotations


def change_layer(pecha_id, content_file, repo, num, metadata):
    pagination_path = content_file.path
    vol_num = Path(f"{pagination_path}").name
    pagination_content = repo.get_contents(f"./{pagination_path}/Pagination.yml")
    pagination_content = pagination_content.decoded_content.decode()
    pagination_content = yaml.safe_load(pagination_content)
    image_group = metadata[num]['image_group']
    pagination_info = get_pagination(image_group)
    annotations  = get_new_annotations(pagination_content, pagination_info)
    if annotations != None:
        change = write_to_file(pecha_id, pagination_content, annotations, image_group, vol_num)
    return change 


def get_layers(g, pecha_id, metadata):
    repo = g.get_repo(f"Openpecha/{pecha_id}")
    contents = repo.get_contents(f"./{pecha_id}.opf/layers")
    for num, content_file in enumerate(contents,1):
        change = change_layer(pecha_id, content_file, repo, num, metadata)

    return change


def get_pagination(image_group):
        # image_group = "I3CN20676"
        r = requests.get(f'https://iiifpres.bdrc.io/bvm/ig:bdr:{image_group}')
        new_pagination = {}
        paginations = {}
        pagination_info = r.json()
        for img in pagination_info:
            if img == "view": 
                imagelist = pagination_info["view"]["view1"]["imagelist"]
                for num, image_info in enumerate(imagelist,1):
                    if 'pagination' in image_info:
                        filename = image_info['filename']
                        pagination = image_info['pagination']['pgfolios']['value']
                    else:
                        filename = image_info['filename']
                        pagination = None
                    paginations[f"{num}"] = {
                        'filename': filename,
                        'pagination': pagination
                    }
                    new_pagination.update(paginations)
                    paginations = {}
        return new_pagination



def get_branch(repo, branch):
    if branch in repo.heads:
        return branch
    return "master"


def get_meta_info(pecha_id):
    metadata = {}
    contents = Path(f"./{pecha_id}/{pecha_id}.opf/meta.yml").read_text(encoding='utf-8')
    meta_content = yaml.safe_load(contents)
    meta = meta_content['source_metadata']['volumes']
    for num, uid in enumerate(meta, 1):
        base_file = None
        image_group = meta[uid]['image_group_id']
        if 'base_file' in meta[uid]:
            base_file = meta[uid]['base_file']
            metadata[num] = {'image_group': image_group, 'base_file': base_file}
        else:
            metadata[num] = {'image_group': image_group}
    return metadata, num

def download_pecha(pecha_id, out_path=None, branch="main"):
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
    token = "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"
    g = Github(token) 
    commit_msg = "pagination added in Pagination.yml"
    pecha_id = "P007112"
    file_path = './'
    pecha_path = download_pecha(pecha_id, file_path)
    metadata, nums = get_meta_info(pecha_id)
    change = get_layers(g, pecha_id, metadata)
    if change == True:
        repo = Repo(pecha_path)
        setup_auth(repo, "ta4tsering", token)
        commit(repo,commit_msg, branch="main")
    clean_dir(pecha_path)