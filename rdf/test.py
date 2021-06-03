import yaml
import csv
import re
import requests
import logging
import shutil
from pathlib import Path
from rdflib import Graph
from git import Repo
from github import Github
from rdflib.namespace import Namespace, RDF

config = {
    "OP_ORG": "https://github.com/ta4tsering"
}

BDR = Namespace("http://purl.bdrc.io/resource/")
BDO = Namespace("http://purl.bdrc.io/ontology/core/")

logging.basicConfig(
    filename="pagination_added.log",
    format="%(levelname)s: %(message)s",
    level=logging.INFO,
)

def clean_dir(layers_output_dir):
    if layers_output_dir.is_dir():
            shutil.rmtree(str(layers_output_dir))


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


def write_to_file(pecha_id, pagination_content, annotations, image_group, vol):
    change = False
    if annotations:
        del pagination_content['annotations']
        pagination_content['image_group_id'] = image_group
        pagination_content[f'annotations'] = annotations
        content_yml = yaml.safe_dump(pagination_content, default_flow_style=False, sort_keys=False,  allow_unicode=True)
        Path(f'./{pecha_id}/{pecha_id}.opf/layers/v{vol:03}/Pagination.yml').write_text(content_yml, encoding='utf-8')
        change = True
    return change

def get_new_annotations(pagination_content, pagination_infos):
    annotations = pagination_content['annotations']
    if annotations != []:
        for uid in annotations:
            imgnum = annotations[uid]['imgnum']
            if imgnum in pagination_infos.keys():
                pagination = pagination_infos[imgnum]['pagination']
            else:
                pagination = None
            annotations[uid]['pagination'] = pagination
    return annotations

def get_gap(gap_start, gap_end):
    if re.search(r"[a|r]", gap_start):
        start = re.sub(r"[a|r]", "", gap_start)
        start = int(start)
        start_side = True
    elif re.search(r"[b|v]", gap_start):
        start = re.sub(r"[b|v]", "", gap_start)
        start = (int(start)+1)
        start_side = False
    else:
        if gap_start != '':
            start = int(gap_start)
            start_side = True
        else:
            start = None
            start_side = None
    if gap_end:
        if re.search(r"[a|r]", gap_end):
            end = re.sub(r"[a|r]", "", gap_end)
            end = int(end)
        elif re.search(r"[b|v]", gap_end):
            end = re.sub(r"[b|v]", "", gap_end)
            end = (int(end)+1)
        else:
            end = int(gap_end)
    else:
        end = None
    return start, end, start_side


def get_content_statement(contentstate):
    # contentstate = "4ff. (p.270-)"
    if re.search(r"[p]", contentstate) != None:
        if re.search(r"[p]|\-", contentstate):
            if re.search(r"[ff\.]", contentstate):
                outputs = re.split(r"[\.]", contentstate)
                state = outputs[-1]
                if re.search(r"(\-)", state):
                    pgs = re.split(r"(\-)", state)
                    pg_start = re.sub(r"\(|\)", "", pgs[0])
                    pg_end = re.sub(r"\(|\)", "", pgs[2])
                else:
                    pg_start = re.sub(r"\(|\)", "", state)
                    pg_end = None
                page_start, page_end, start_side = get_gap(pg_start, pg_end)
        else:
            return None, None, None
    else:
        if re.search(r"[\(|\)]", contentstate):
            outputs = re.split(r"[\(]", contentstate)
            state = outputs[-1]
            if re.search(r"(\-)", state):
                pgs = re.split(r"(\-)", state)
                pg_start = re.sub(r"\(|\)", "", pgs[0])
                pg_end = re.sub(r"\(|\)", "", pgs[2])
            else:
                pg_start = re.sub(r"\(|\)", "", state)
                pg_end = None
            page_start, page_end, start_side = get_gap(pg_start, pg_end)
        else:
            return None, None, None
    return page_start, page_end, start_side
        

def get_pagination(page_info, vol_num):
    pagination_info = {}
    pagination = {}
    keylist = sorted(page_info.keys())
    for img_start in keylist:
        # if int(img_start) != 567:
        #     continue
        img_end = page_info[img_start]['end']
        contentstate = page_info[img_start]['loc_statement']
        page_start, page_end, start_side = get_content_statement(contentstate)
        if img_end == None and page_end != None:
            page_gap = page_end - page_start
            img_end = int(img_start) + int((page_gap * 2) + 1)
        img_gap = int(img_end) - int(img_start)
        if page_start:
            if page_end == None and img_gap > 1:
                page_end = int(page_start + (img_gap - 1)/2)
        num = 1
        page_diff = 1
        count = 0
        if page_start:
            for imgnum in range(int(img_start), (int(img_end)+1)):
                if page_end:
                    for page_num in range(page_start, page_end+1):
                        img_diff = imgnum - int(img_start)
                        if img_diff != 0:
                            if count == 2:
                                page_diff += 1
                                count = 0
                                page_num += (img_diff - page_diff) 
                                count += 1
                            else:
                                page_num += (img_diff - page_diff) 
                                count += 1
                            if start_side == True:
                                if num % 2 != 0:
                                    page_num = f"{page_num}a"
                                elif num % 2 == 0:
                                    page_num = f"{page_num}b"
                            elif start_side == False:
                                if num % 2 == 0:
                                    page_num = f"{page_num}a"
                                elif num % 2 != 0:
                                    page_num = f"{page_num}b"
                        else:
                            if start_side == True:
                                if num % 2 != 0:
                                    page_num = f"{page_start}a"
                                elif num % 2 == 0:
                                    page_num = f"{page_start}b"
                            elif start_side == False:
                                if num % 2 == 0:
                                    page_num = f"{page_start}a"
                                elif num % 2 != 0:
                                    page_num = f"{page_start}b"
                        pagination_info[imgnum] = {'pagination': page_num}
                        pagination.update(pagination_info)
                        pagination_info = {}
                        num += 1
                        break
                else:
                    if start_side == True:
                        if num % 2 != 0:
                            page_num = f"{page_start}a"
                        elif num % 2 == 0:
                            page_num = f"{page_start}b"
                    else:
                        if num % 2 == 0:
                            page_num = f"{page_start}a"
                        elif num % 2 != 0:
                            page_num = f"{page_start}b"
                    pagination_info[imgnum] = {'pagination': page_num}
                    pagination.update(pagination_info)
                    pagination_info = {}
                    num += 1
                    break
    paginations = yaml.safe_dump(pagination)
    Path(f"./pgfolio/{vol_num}.yml").write_text(paginations, encoding='utf-8')
    return pagination
                


def get_new_layer(pecha_id, loc_info, metadata):
    for vol_num, page_info in loc_info.items():
        # if int(vol_num) != 9:
        #     continue 
        pagination_info = get_pagination(page_info, vol_num)
        vol = int(vol_num)
        content = Path(f"./{pecha_id}/{pecha_id}.opf/layers/v{vol:03}/Pagination.yml").read_text(encoding='utf-8')
        pagination_content = yaml.safe_load(content)
        image_group = metadata[vol]['image_group']
        annotations  = get_new_annotations(pagination_content, pagination_info)
        if annotations != None:
            change = write_to_file(pecha_id, pagination_content, annotations, image_group, vol)
    return change 


def get_content_info(g, id):
    end = None
    for vol_num in g.objects(BDR[id], BDO.contentLocationVolume):
        vol = get_id(str(vol_num))
        for pg_start in g.objects(BDR[id], BDO.contentLocationPage):
            start = get_id(str(pg_start))
            for pg_end in g.objects(BDR[id], BDO.contentLocationEndPage):
                end = get_id(str(pg_end))
    return vol, start, end


def get_location_info(g, nodes):
    loc_info = {}
    curr_loc = {}
    for node in nodes:
        for contentlocation in g.objects(BDR[node], BDO.contentLocation):
            for contentstatement in g.objects(BDR[node], BDO.contentLocationStatement):
                loc_id = get_id(str(contentlocation))
                loc_state = get_id(str(contentstatement))
                vol, start, end = get_content_info(g, loc_id)
                if vol in loc_info.keys():
                    curr_loc[start]={
                        'end': end,
                        'loc_statement': loc_state
                    }
                    loc_info[vol].update(curr_loc)
                    curr_loc = {}
                else:
                    curr_loc[vol]={
                        start:{
                            'end': end,
                            'loc_statement': loc_state
                        }
                    }
                    loc_info.update(curr_loc)
                    curr_loc = {}
    loc_yml = yaml.safe_dump(loc_info)
    Path(f"./location.yml").write_text(loc_yml, encoding='utf-8')
    return loc_info

def get_only_nodes(g, ids):
    node_list = []
    for id in ids:
        for contentstatement in g.objects(BDR[id], BDO.contentLocationStatement):
            if contentstatement:
                node_list.append(id)
    return node_list

def get_id(URI):
    return URI.split("/")[-1]

def parse_ttl_info(meta_ttl, work_id):
    ids = []
    work_id = f"M{work_id}"
    g = Graph()
    try:
        g.parse(data=meta_ttl, format="ttl")
    except:
        print(f"{work_id}.ttl Contains bad syntax")
        return {}
    for instance in g.subjects(RDF.type, BDO.Instance):
        for haspart in g.objects(instance, BDO.hasPart):
            id = get_id(str(haspart))
            ids.append(id)
    return g, ids

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
    # get_content_statement()
    token = "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"
    g = Github(token) 
    commit_msg = "pagination added in Pagination.yml"

    pecha_id = "P003244"
    file_path = './'
    # pecha_path = download_pecha(pecha_id, file_path)
    work_id, metadata = get_work_id(pecha_id)
    meta_ttl = get_ttl(work_id)
    g, ids = parse_ttl_info(meta_ttl, work_id)
    node_ids = get_only_nodes(g, ids)
    loc_info = get_location_info(g,node_ids)
    change = get_new_layer(pecha_id, loc_info, metadata)
    if change == True:
        repo = Repo(pecha_path)
        setup_auth(repo, "ta4tsering", token)
        commit(repo,commit_msg, branch="main")
    clean_dir(pecha_path)
    