import csv
import git 
import requests
import logging
import os
import re
import shutil
import yaml

from git import Repo 
from github import Github 
from pathlib import Path 


config = {
    "OP_ORG": "https://github.com/Openpecha"
}


logging.basicConfig(
    filename="new_pagination_updated.log",
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

def get_new_annotations(pagination_content,pagination_path, img2seq, names):
    vol_num = Path(f"{pagination_path}").name
    new_pagination = {}
    pagination = {}
    changed = False
    paginations = pagination_content['annotations']
    for name in names:
        if changed == True:
            break
        for _num, uuid in enumerate(paginations,1):
            if 'imgnum' in paginations[uuid]:
                changed = True
                break
            elif paginations[uuid]['reference'] == name or paginations[uuid]['reference'] == name[1:]:
                if paginations[uuid]['page_info'] != None:
                    new_pagination[f"{uuid}"] = { 
                        'imgnum': img2seq[name]['num'],
                        'page_info': paginations[uuid]['page_info'],
                        'reference': paginations[uuid]['reference'] + ('.') + img2seq[name]['ext'],
                        'span':{
                            'start': pagination[uuid]['span']['start'],
                            'end': pagination[uuid]['span']['end']
                        }
                    }
                    pagination.update(new_pagination)
                    new_pagination = {}
                else:
                    new_pagination[f"{uuid}"] = { 
                        'imgnum': img2seq[name]['num'],
                        'reference': paginations[uuid]['reference'] + ('.') + img2seq[name]['ext'],
                        'span':{
                            'start': paginations[uuid]['span']['start'],
                            'end': paginations[uuid]['span']['end']
                        }
                    }
                    pagination.update(new_pagination)
                    new_pagination = {}
    return pagination, vol_num
            


def get_pagination_content(content_file, repo, pecha_id, img2seq, names):
    pagination_path = content_file.path
    pagination_content = repo.get_contents(f"./{pagination_path}/Pagination.yml")
    pagination_content = pagination_content.decoded_content.decode()
    pagination_content = yaml.safe_load(pagination_content)
    pagination, vol_num = get_new_annotations(pagination_content, pagination_path, img2seq, names)
    if pagination:
        return pagination, pagination_content, vol_num
    else:
        return None, None, None 


def get_new_layers(g, pecha_id, img_groups):
    repo = g.get_repo(f"Openpecha/{pecha_id}")
    contents = repo.get_contents(f"./{pecha_id}.opf/layers")
    change = False
    for num, content_file in enumerate(contents, 0):
        img2seq, names = get_imagelist(img_groups[num])
        if img2seq != None:
            pagination, pagination_content, vol_num = get_pagination_content(content_file, repo, pecha_id, img2seq, names)
            response = not bool(pagination)
            if response == False:
                del pagination_content['annotations']
                pagination_content[f'annotations'] = pagination
                content_yml = yaml.safe_dump(pagination_content, default_flow_style=False, sort_keys=False,  allow_unicode=True)
                Path(f"./{pecha_id}/{pecha_id}.opf/layers/{vol_num}/Pagination.yml").write_text(content_yml, encoding='utf-8')
                change = True
    return change

def get_img_groups(g, pecha_id):
    repo = g.get_repo(f"Openpecha/{pecha_id}")
    contents = repo.get_contents(f"./{pecha_id}.opf/meta.yml")
    meta_content = contents.decoded_content.decode()
    meta_data = yaml.safe_load(meta_content)
    img_groups = []
    volumes = meta_data['source_metadata']['volumes']
    for vol_id, vol_info in volumes.items():
            img_group = vol_info['image_group_id']
            img_groups.append(img_group)
    return img_groups

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


def get_imagelist(img_group):
    try:
        r = requests.get(f"http://iiifpres.bdrc.io/il/v:bdr:{img_group}")
        img2seq = {}
        names = []
        for i, img in enumerate(r.json(), start=1):
            name, ext = img["filename"].split(".")
            img2seq[name] = {"num": i, "ext": ext}
            names.append(name)
        return img2seq, names 
    except:
        print("img2seq response error")
        return None, None

if __name__=='__main__':
    token = ""
    g = Github(token) 
    commit_msg = "added imgnum to the pagination"
    pecha_id = "P000006"
    file_path = './'
    pecha_path = download_pecha(pecha_id, file_path)
    img_groups = get_img_groups(g, pecha_id)
    change = get_new_layers(g, pecha_id, img_groups)
    if change == True:
        repo = Repo(pecha_path)
        setup_auth(repo, "Openpecha", token)
        commit(repo,commit_msg, branch="master")
        clean_dir(pecha_path)
