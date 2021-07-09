import subprocess 
import csv
import logging
import os
import re
import sys
import requests
import shutil
import uuid
import yaml
import pyewts

from git import Repo 
from github import Github 
from pathlib import Path 
from pybo.cli import tok
from rdflib import Graph
from rdflib.namespace import RDF, RDFS, SKOS, OWL, Namespace, NamespaceManager, XSD


BDR = Namespace("http://purl.bdrc.io/resource/")
BDO = Namespace("http://purl.bdrc.io/ontology/core/")
EWTSCONV = pyewts.pyewts()

config = {
    "OP_ORG": "https://github.com/ta4tsering"
}


logging.basicConfig(
    filename="Release_created.log",
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
            # notifier(f"{pecha_id} pagination updated")
            # print(f"{pecha_id} pagination updated")

def get_new_release(release_yml, bopho_title, pecha_id):
    yes = "on"
    release = {}
    release_project = release_yml['jobs']['release-project']['steps'][5]
    release_project = release_yml['jobs']['release-project']['steps'][5]
    if release_project['name'] == "upload plain assets" :
        release_project['with']['asset_name'] = f"{bopho_title}_plain_{pecha_id}.zip"
        release_yml['jobs']['release-project']['steps'][5] = release_project
    release_project = release_yml['jobs']['release-project']['steps'][6]
    if release_project['name'] == "upload pages assets" :
        release_project['with']['asset_name'] = f"{bopho_title}_pages_{pecha_id}.zip"
        release_yml['jobs']['release-project']['steps'][6] = release_project
    release['name'] = "create release"
    release[f"{yes}"] = {
                'push':{
                'paths-ignore':f'**/README.md'
                }
    }
    release['jobs'] = release_yml['jobs']
    return release

def get_release_yaml():
    content = Path(f"./create_release.yml").read_text(encoding='utf-8')
    release_yml = yaml.safe_load(content)
    return release_yml

def get_english_pronunciation(title):
    title_output = subprocess.run(f"bo tok-string '{title}'", capture_output=True, shell=True, text=True)
    segmented_title = re.split(f"(\\\n)", title_output.stdout)
    title_done = segmented_title[2]
    print(title_done)
    title_segments = re.split(f"(\s)", title_done)
    title_segment_all = []
    final_titles = []
    for num, title_segment in enumerate(title_segments,1):
        if num%2 != 0:
            Path(f"./input.txt").write_text(title_segment, encoding='utf-8')
            subprocess.run('perl ./bin/pronounce.pl ./input.txt ./output.txt', shell=True)
            title_english = Path(f"./output.txt").read_text(encoding='utf-8')
            title_english_segments  = re.split(f"(\s)",title_english)
            title_segment_all = []
            for num, title_segment in enumerate(title_english_segments, 1):
                if num%2 != 0:
                    title_segment_all.append(title_segment)
            s = ''.join(title_segment_all)
            final_titles.append(s)
    title_list = []
    for num, final_title in enumerate(final_titles):
        if final_title != '':
            title_list.append(final_title)
    final_string = '_'.join(title_list)
    return final_string

def get_meta_title(g, pecha_id):
    repo = g.get_repo(f"Openpecha/{pecha_id}")
    contents = repo.get_contents(f"./{pecha_id}.opf/meta.yml")
    content = contents.decoded_content.decode()
    meta_data = yaml.safe_load(content)
    title = meta_data['source_metadata']['title']
    tib = None
    return title, tib

def ewtstobo(ewtsstr):
    res = EWTSCONV.toUnicode(ewtsstr)
    return res


def get_title_id(URI):    
    return URI.split("/")[-1]

def get_title_ids(g, work_id):
    title_ids = []
    volumes = g.objects(BDR[work_id], BDO["hasTitle"])
    for volume in volumes:
        title_id = get_title_id(str(volume))
        title_ids.append(title_id)
    return title_ids

def parse_title_info(meta_ttl, work_id):
    eng_title = []
    title_list = []
    work_id = f"M{work_id}"
    g = Graph()
    try:
        g.parse(data=meta_ttl, format="ttl")
    except:
        logging.warning(f"{work_id}.ttl Contains bad syntax")
        return {}
    title_ids = get_title_ids(g, work_id)
    title_ids.sort()
    for title_id in title_ids:
        print(title_id)
        title = g.value(BDR[title_id], RDFS.label)
        if title.language == "bo-x-ewts":
            title_list.append(title)
        else:
            if title.language == "en":
                eng_title.append(title)
            elif title.language == "zh-latn-pinyin-x-ndia":
                eng_title.append(title)
    if len(title_list) >= 2:
        print(f"this is the legth {len(title_list)}")
        for num, title in enumerate(title_list,0):
            if num == 0:
                min_title = title_list[num]
            else:
                if len(title_list[num]) <  len(min_title):
                    min_title = title_list[num]
        final_title = ewtstobo(min_title)
        tib = True
        return final_title, tib
    else:
        if len(title_list) != 0:
            title = title_list[0]
            final_title = ewtstobo(title)
            tib = True
            return final_title, tib
        elif len(eng_title) != 0:
            tib = False
            print(f"this is the legth {len(eng_title)}")
            for num,title in enumerate(eng_title, 0):
                if num == 0:
                    min_title = eng_title[num]
                else:
                    if len(eng_title[num]) < len(min_title):
                        min_title = eng_title[num]
            print(min_title)
            return min_title,tib

def get_ttl(work_id):
    try:
        ttl = requests.get(f"http://purl.bdrc.io/graph/M{work_id}.ttl")
        return ttl.text
    except:
        print(' TTL not Found!!!')
        return None



def check_pagination(g, pecha_id):
    repo = g.get_repo(f"Openpecha/{pecha_id}")
    contents = repo.get_contents(f"./{pecha_id}.opf/layers")
    for content_file in contents:
        pagination_path = content_file.path
        pagination_content = repo.get_contents(f"./{pagination_path}/Pagination.yml")
        pagination_content = pagination_content.decoded_content.decode()
        pagination_content = yaml.safe_load(pagination_content)
        annotations = pagination_content["annotations"]
        for uid, pg_info in annotations.items():
            if "pagination" in pg_info.keys():
                pg = True
                break
            else:
                pg = False
                break
        return pg


def get_tags(pecha_id):
    tags = subprocess.run(f'cd ./{pecha_id}; git tag', shell=True, capture_output=True, text=True)
    tag = tags.stdout
    tags = re.split(f"\\\n", tag)
    highest_tag = 0
    for _, tag in enumerate(tags, 1):
        if tag:
            tag = float(tag[1:])
            if highest_tag <= tag:
                highest_tag = tag
    return int(highest_tag)

def get_id(g, pecha_id):
    repo = g.get_repo(f"Openpecha/{pecha_id}")
    contents = repo.get_contents(f"./{pecha_id}.opf/meta.yml")
    content = contents.decoded_content.decode()
    meta_data = yaml.safe_load(content)
    work_id = meta_data['source_metadata']['id'][4:]
    return work_id

def get_branch(repo, branch):
    if branch in repo.heads:
        return branch
    return "main"


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


def setup_auth(repo, org, token):
    remote_url = repo.remote().url
    old_url = remote_url.split("//")
    authed_remote_url = f"{old_url[0]}//{org}:{token}@{old_url[1]}"
    repo.remote().set_url(authed_remote_url)


if __name__=='__main__':
    token = "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"
    g = Github(token) 
    commit_msg = "added github action to create realease"
    # with open("catalog.csv", newline="") as csvfile:
    #     pechas = list(csv.reader(csvfile, delimiter=","))
    #     for pecha in pechas[3992:4303]:
    #         pecha_id = re.search("\[.+\]", pecha[0])[0][1:-1]
    pecha_id = "P000511"
    file_path = './'
    pecha_path = download_pecha(pecha_id, file_path)
    github_action_path = Path(f"{pecha_path}/.github/workflows/")
    github_action_path.mkdir(exist_ok=True, parents=True)
    work_id = get_id(g, pecha_id)
    tag = get_tags(pecha_id)
    print(tag)
    if tag == 0:
        pg = check_pagination(g, pecha_id)
        if pg != True:
            ttl = get_ttl(work_id)
            if ttl:
                title,tib = parse_title_info(ttl, work_id)
            else:
                title, tib = get_meta_title(g, pecha_id)
            if title != None:
                if tib == True:
                    bopho_title = get_english_pronunciation(title)
                    if len(bopho_title) > 30:
                        bopho_title = bopho_title[0:30]
                elif tib == False:
                    if len(title) > 30:
                        bo_title = title[0:30]
                        bopho_title = re.sub(r"\s", "_", bo_title)
                    else:
                        bopho_title = re.sub(r"\s", "_", title)
                print(bopho_title)
                release_yml = get_release_yaml()
                edited_release = get_new_release(release_yml, bopho_title, pecha_id)
                if edited_release :
                    create_release_yml = yaml.safe_dump(edited_release, default_flow_style=False, sort_keys=False,  allow_unicode=True)
                    Path(f"./{pecha_id}/.github/workflows/create_release.yml").write_text(create_release_yml, encoding='utf-8')
                    repo = Repo(pecha_path)
                    setup_auth(repo, "ta4tsering", token)
                    commit(repo,commit_msg, branch="main")
                    print("added github action")
                    clean_dir(pecha_path)
        else:
            clean_dir(pecha_path)
            
            