import csv
import git 
import logging
import os
import re
import shutil
import requests
import pyewts
import yaml

from git import Repo 
from github import Github 
from pathlib import Path 
from rdflib import Graph
from rdflib.namespace import RDF, RDFS, Namespace




config = {
    "OP_ORG": "https://github.com/ta4tsering"
}

BDR = Namespace("http://purl.bdrc.io/resource/")
BDO = Namespace("http://purl.bdrc.io/ontology/core/")
EWTSCONV = pyewts.pyewts()


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
        for uid in annotations:
            imgnum = annotations[uid]['imgnum']
            if imgnum in pagination_info.keys():
                pagination = pagination_infos[imgnum]['pagination']
            else:
                pagination = None
            annotations[uid]['pagination'] = pagination
    return annotations


def change_layer(pecha_id, content_file, repo, pagination_info, metadata, num):
    pagination_path = content_file.path
    vol_num = Path(f"{pagination_path}").name
    pagination_content = repo.get_contents(f"./{pagination_path}/Pagination.yml")
    pagination_content = pagination_content.decoded_content.decode()
    pagination_content = yaml.safe_load(pagination_content)
    image_group = metadata[num]['image_group']
    annotations  = get_new_annotations(pagination_content, pagination_info)
    if annotations != None:
        change = write_to_file(pecha_id, pagination_content, annotations, image_group, vol_num)
    return change 


def get_layers(g, pecha_id, pagination_info, metadata):
    repo = g.get_repo(f"Openpecha/{pecha_id}")
    contents = repo.get_contents(f"./{pecha_id}.opf/layers")
    for num, content_file in enumerate(contents,1):
        change = change_layer(pecha_id, content_file, repo, pagination_info, metadata, num)

    return change


def get_id(URI):    
    return URI.split("/")[-1]

def get_paginations(location_info, location_id, pg_start, pg_end, start_img, end_img, diff, num):
    pagination = {}
    pagination_info = {}
    if pg_end != None:
        if diff == 0:
            if location_id == location_info[num]['location_id']:
                for pg_num in range(pg_start, pg_end):
                    pg_diff = pg_num - pg_start
                    for img_num in range(start_img, end_img):
                        img_num += pg_diff
                        pagination_info[img_num] = {'pagination': pg_num}
                        pagination.update(pagination_info)
                        pagination_info = {}
                        break
            else:
                return None
        elif diff == 1:
            if location_id == location_info[num]['location_id']:
                for pg_num in range(pg_start, pg_end):
                    for img_num in range(start_img, end_img):
                        pagination_info[img_num] = {'pagination': pg_num}
                        pagination.update(pagination_info)
                        pagination_info = {}
                        break
            else:
                return None      
        return pagination
    else:
        return None



def get_paginations_info(g, location_info, location_ids):
    pagination_info = {}
    for location_id in location_ids:
        start_imgs = g.objects(BDR[location_id], BDO["contentLocationPage"])
        for start_img in start_imgs:
            start_img = int(get_id(start_img))
            print(start_img)
        end_imgs = g.objects(BDR[location_id], BDO["contentLocationEndPage"])
        for end_img in end_imgs:
            end_img = int(get_id(end_img))
            print(end_img)
        if end_img == start_img:
            img_diff = end_img
        else:
            img_diff = int(end_img) - int(start_img)
        for num in location_info:
            pagination = location_info[num]['content_page']
            if re.match(r"(pp\.)", pagination):
                pp, pg_num = re.split(r"pp\.\s", pagination)
                if re.search(r"(\-)", pg_num):
                    pgs = re.split(r"(\-)", pg_num)
                    pg_start = int(pgs[0])
                    pg_end = int(pgs[2])
                    pg_diff = pg_end - pg_start
                    if pg_diff == img_diff:
                        diff = 0
                    else:
                        diff = 1
                    paginations = get_paginations(location_info, location_id, pg_start, pg_end, start_img, end_img, diff, num)
                else:
                    pg_diff = pg_num
                    diff = 2
                    paginations = get_paginations(location_info, location_id, pg_num, None, start_img, None, diff, num)
                if paginations:
                    pagination_info.update(paginations)
                    print(len(pagination_info))
                    break
    content_yml = yaml.safe_dump(pagination_info)
    Path(f"./pgfolio/list.yml").write_text(content_yml, encoding='utf-8')
    return pagination_info


def get_location_info(g,pg_ids):
    location_info = {}
    location_infos = {}
    location_ids = []
    for num, pg_id in enumerate(pg_ids,1):
        content_location_ids = g.objects(BDR[pg_id], BDO["contentLocation"])
        for content_location_id in content_location_ids:
            location_id = get_id(content_location_id)
            content_pages = g.objects(BDR[pg_id], BDO["contentLocationStatement"])
            for content_page in content_pages:
                content_page = get_id(content_page)
                location_info[num] = {
                    'location_id': location_id,
                    'content_page': content_page
                }
                location_infos.update(location_info)
                location_info = {}
        location_ids.append(location_id)
    return location_infos, location_ids


def get_pg_ids(g, work_id):
    work_id = f"M{work_id}"
    pg_ids = []
    parts = g.objects(BDR[work_id], BDO["hasPart"])
    for part in parts:
        pg_id = get_id(str(part))
        pg_ids.append(pg_id)
    print(pg_ids)
    return pg_ids


def parse_ttl_info(meta_ttl, work_id):
    work_id = f"{work_id}"
    g = Graph()
    try:
        g.parse(data=meta_ttl, format="ttl")
    except:
        logging.warning(f"{work_id}.ttl Contains bad syntax")
        return {}
    pg_ids = get_pg_ids(g, work_id)
    location_info, location_ids = get_location_info(g, pg_ids)
    pagination_info = get_paginations_info(g, location_info, location_ids)
    return pagination_info


def get_ttl(work_id):
    try:
        ttl = requests.get(f"http://purl.bdrc.io/graph/M{work_id}.ttl")
        return ttl.text
    except:
        print(' TTL not Found!!!')
        return None


def get_work_id(pecha_id):
    metadata = {}
    contents = Path(f"./{pecha_id}/{pecha_id}.opf/meta.yml").read_text(encoding='utf-8')
    meta_content = yaml.safe_load(contents)
    work_id = meta_content['source_metadata']['id'][4:]
    meta = meta_content['source_metadata']['volumes']
    for num, uid in enumerate(meta, 1):
        base_file = None
        image_group = meta[uid]['image_group_id']
        if 'base_file' in meta[uid]:
            base_file = meta[uid]['base_file']
            metadata[num] = {'image_group': image_group, 'base_file': base_file}
        else:
            metadata[num] = {'image_group': image_group}
    return work_id, metadata

def setup_auth(repo, org, token):
    remote_url = repo.remote().url
    old_url = remote_url.split("//")
    authed_remote_url = f"{old_url[0]}//{org}:{token}@{old_url[1]}"
    repo.remote().set_url(authed_remote_url)

def get_branch(repo, branch):
    if branch in repo.heads:
        return branch
    return "master"

def download_pecha(pecha_id, out_path=None, branch="main"):
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

if __name__=='__main__':
    token = "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"
    g = Github(token) 
    commit_msg = "pagination added in Pagination.yml"
    pecha_id = "P002910"
    file_path = './'
    pecha_path = download_pecha(pecha_id, file_path)
    work_id, metadata = get_work_id(pecha_id)
    meta_ttl = get_ttl(work_id)
    pagination_info  = parse_ttl_info(meta_ttl, work_id)
    if pagination_info:
        change = get_layers(g, pecha_id, pagination_info, metadata)
        if change == True:
            repo = Repo(pecha_path)
            setup_auth(repo, "ta4tsering", token)
            commit(repo,commit_msg, branch="main")
    clean_dir(pecha_path)