import csv
import re
import yaml
import logging

from github import Github 
from pathlib import Path

logging.basicConfig(
    filename="metadata_updated.log",
    format="%(levelname)s: %(message)s",
    level=logging.INFO,
)

def notifier(msg):
    logging.info(msg)

def update_repo(g, pecha_id, file_path, commit_msg, new_content):
    try:
        repo = g.get_repo(f"Openpecha/{pecha_id}")
        contents = repo.get_contents(f"{file_path}", ref="master")
        repo.update_file(contents.path, commit_msg, new_content, sha=contents.sha, branch="master")
        notifier( f'Pecha id :{pecha_id} updated ')
    except Exception as e:
        notifier( f'Pecha id :{pecha_id} not updated with error {e}')


def add_base(meta_data, pagintion_info):
    volumes = meta_data['source_metadata']['volumes']
    if volumes != (None or ''):
        for info_num, pg_info in pagination_info.items():
            image_group = pg_info['Image_group']
            vol_num = pg_info['Vol']
            for vol_id, vol_info in volumes.items():
                if vol_info['image_group_id'][1:] == image_group:
                    vol_info['base_file'] = f"{vol_num}.txt"
                    break
                elif vol_info['image_group_id'] == image_group:
                    vol_info['base_file'] = f"{vol_num}.txt"
                    break
    else:
        notifier( f'Pecha id :{pecha_id} no volumes with error {e}')
    return meta_data

def get_new_meta( meta_data, pagination_info, pecha_id):
    if meta_data['initial_creation_type'] =='ocr':
        meta_data['id'] = pecha_id
        meta_data['source_metadata']['volumes'] = meta_data['source_metadata']['volume']
        del meta_data['source_metadata']['volume']
        meta_data = add_base(meta_data, pagination_info)
    meta_yml = yaml.safe_dump(meta_data, default_flow_style=False, sort_keys=False,  allow_unicode=True)
    return meta_yml

def get_image_group_and_vol_num(pagination_content,pagination_path):
    vol_num = Path(f"{pagination_path}").name
    paginations = pagination_content['annotations']
    if paginations != []:
        for pg_uuid, pg_info in enumerate(paginations,1):
            image_group = paginations[pg_info]['reference'][:-8]
            return image_group, vol_num
    else:
        return None, None


def get_pagination_content(g, pagination_path, pecha_id, repo):
    pagination_path = pagination_path.path
    pagination_content = repo.get_contents(f"./{pagination_path}/pagination.yml")
    pagination_content = pagination_content.decoded_content.decode()
    pagination_content = yaml.safe_load(pagination_content)
    image_group, vol_num = get_image_group_and_vol_num(pagination_content, pagination_path)
    return image_group, vol_num


def get_pagination_info(g, pecha_id, meta_data):
    layers = []
    pagination_info = {}
    cur_text = {}
    volumes = meta_data['source_metadata']['volume']
    if volumes != (None or '') :
        repo = g.get_repo(f"Openpecha/{pecha_id}")
        contents = repo.get_contents(f"./{pecha_id}.opf/layers")
        num = 1
        for content_file in contents:
            image_group, vol_num = get_pagination_content(g, content_file, pecha_id, repo)
            if image_group and vol_num != None:
                cur_text[f'{num}'] = {
                    'Image_group': image_group,
                    'Vol': vol_num
                }
                pagination_info.update(cur_text)
                num += 1
                cur_text = {}
            else:
                return None
        return pagination_info
    else:
        return None



def get_meta_from_opf(g, pecha_id):
    try:
        repo = g.get_repo(f"Openpecha/{pecha_id}")
        contents = repo.get_contents(f"./{pecha_id}.opf/meta.yml")
        return contents.decoded_content.decode()
    except:
        print('Repo Not Found')
        notifier( f'Pecha id :{pecha_id} not updated due to repo not found')
        return None


if __name__ == "__main__":
    token = ''
    g = Github(token)
    commit_msg = 'meta updated'

    with open("catalog.csv", newline="") as csvfile:
        pechas = list(csv.reader(csvfile, delimiter=","))
        for pecha in pechas[324:353]:
            pecha_id = re.search("\[.+\]", pecha[0])[0][1:-1]
            file_path = f"./{pecha_id}.opf/meta.yml"
            old_meta_data = get_meta_from_opf(g, pecha_id)
            if old_meta_data != None:
                old_meta_data = yaml.safe_load(old_meta_data)
                pagination_info = get_pagination_info(g, pecha_id, old_meta_data)
                if pagination_info != None:
                    new_meta_data = get_new_meta(old_meta_data, pagination_info, pecha_id)
                    if new_meta_data != None:
                        update_repo(g, pecha_id, file_path, commit_msg, new_meta_data)
                        print(f'INFO: {pecha_id} meta updated..')