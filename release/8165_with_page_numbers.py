import os 
import re
import yaml
import requests
import shutil
import logging
from zipfile36 import ZipFile
from os.path import basename
from pathlib import Path
from openpecha.serializers import HFMLSerializer
from rdflib import Graph
from rdflib.namespace import RDF, RDFS, SKOS, OWL, Namespace, NamespaceManager, XSD

BDR = Namespace("http://purl.bdrc.io/resource/")
BDO = Namespace("http://purl.bdrc.io/ontology/core/")


def write_text(content, new_path, vol_num, volume_title, _type):
    if volume_title == None:
        out_fn = Path(f"{new_path}/v{vol_num}_{_type}.txt")
        out_fn.write_text(content)
    else:
        out_fn = Path(f"{new_path}/v{vol_num}_{volume_title}_{_type}.txt")
        out_fn.write_text(content)

def create_zip(base_path, name):
              with ZipFile(name, 'w') as zipObj:
                  for folderName, subfolders, filenames in os.walk(base_path):
                      for filename in filenames:
                          filePath = os.path.join(folderName, filename)
                          zipObj.write(filePath, basename(filePath))


# def page_number_the_content(new_content):
#     length_ = 0
#     for num, line in enumerate(new_content,1):
#         if line == "\n":
#             length_ += 1
#         if length_ == 3:
#             if re.search(f"(\d+)", new_content[num]):
#                 m = re.search(f"(\d+)", new_content[num])
#                 page_num = m.groups(0)



def get_clean_pages(lines, uid):
    new_line = []
    new_content = " "
    for num, line in enumerate(lines,1):
        if  num % 2 != 0:
            new_line = re.sub(f"(\[((.\d+\w)|(\d+(a|b)\.\d+)|(\.\d+))\])", "", line )
            new_content += new_line
            new_line = []
        else:
            new_content += "\n"
    # numbered_content = page_number_the_content(new_content)
    new_content += f"OpenPechaUUID: {uid}"
    return new_content


def change_file_name_pages(pages, pages_path, meta_info, vol_title):
    _type = "pages"
    if vol_title == False:
        for num, vol in enumerate(pages,1):
            vol_num = vol[1:]
            for info_num, meta in meta_info.items():
                vol = meta['vol_num']
                new_vol = f"{vol:03}"
                if new_vol == vol_num:
                    uid = meta['uid']
                    image_group = meta['image_group']
                    content = pages[f'v{vol_num}']
                    lines = re.split(f"(\\\n)", content)
                    page_content = get_clean_pages(lines,uid)
                    write_text(page_content, pages_path, vol_num, None, _type)
                    break
    elif vol_title == True:
        for num, vol in enumerate(pages,1):
            vol_num = vol[1:]
            for info_num, meta in meta_info.items():
                vol = meta['vol_num']
                new_vol = f"{vol:03}"
                if new_vol == vol_num:
                    uid = meta['uid']
                    image_group = meta['image_group']
                    volume_title = meta['title']
                    content = pages[f'v{vol_num}']
                    lines = re.split(f"(\\\n)", content)
                    pages_content = get_clean_pages(lines, uid)
                    write_text(lines, pages_path, vol_num, volume_title, _type)
                    break


def get_pages(opf_path):
    serializer = HFMLSerializer(opf_path, layers=["Pagination"])
    serializer.apply_layers()
    results = serializer.get_result()
    return results


def get_file_name_info(vol_info, meta_info, nums):
    for num in nums:
        for info_num, meta in meta_info.items():
            if meta['image_group'] == vol_info[num]["image_group_id"]:
                if vol_info[num]["title"]:
                    cur_text[num] = { 
                    'image_group': meta['image_group'],
                    'vol_num': meta['vol_num'],
                    'uid': meta['uid'],
                    'title': vol_info[num]["title"]
                    }
                    filename_info.update(cur_text)
                    num += 1
                    cur_text = {}
            else:
                cur_text[num] = { 
                'image_group': meta['image_group'],
                'vol_num': meta['vol_num'],
                'uid': meta['uid'],
                }
                filename_info.update(cur_text)
                num += 1
                cur_text = {}
        return filename_info




def get_img_grp_id(URI):    
    return URI.split("/")[-1]


def get_vol_img_grp_id_list(g, work_id):
    vol_img_grp_ids = []
    volumes = g.objects(BDR[work_id], BDO["instanceHasVolume"])
    for volume in volumes:
        vol_img_grp_id = get_img_grp_id(str(volume))
        vol_img_grp_ids.append(vol_img_grp_id)
    vol_img_grp_ids.sort()
    return vol_img_grp_ids


def parse_volume_info(meta_ttl, work_id):
    g = Graph()
    try:
        g.parse(data=meta_ttl, format="ttl")
    except:
        logging.warning(f"{work_id}.ttl Contains bad syntax")
        return {}
    vol_img_grp_ids = get_vol_img_grp_id_list(g, work_id)
    vol_info = {}
    num = 1
    for vol_img_grp_id in vol_img_grp_ids:
        title = g.value(BDR[vol_img_grp_id], RDFS.comment)
        if title:
            title = title.value
            vol_info[num] = {
                "image_group_id": vol_img_grp_id,
                "title": title,
            }
            num +=1
    if num == 1:
        return None, None
    return vol_info, num

    
def get_ttl(work_id):
    try:
        ttl = requests.get(f"http://purl.bdrc.io/graph/{work_id}.ttl")
        return ttl.text
    except:
        print(' TTL not Found!!!')
        return None

def get_meta_info(meta_data):
    work_id = meta_data['source_metadata']['id'][4:] 
    volumes = meta_data['source_metadata']['volumes']
    cur_text = {}
    meta_info = {}
    num = 1
    for uid, vol_info in volumes.items():
        image_group = vol_info['image_group_id']
        vol_num = vol_info['volume_number']
        cur_text[num] = { 
            'image_group': image_group,
            'vol_num': vol_num,
            'uid': uid
        }
        meta_info.update(cur_text)
        num += 1
        cur_text = {}
    return meta_info, work_id


if __name__=="__main__":
    pecha_id = 'P008165'
    opf_path = Path(f'./{pecha_id}/{pecha_id}.opf')
    meta_content = Path(f'./{pecha_id}/{pecha_id}.opf/meta.yml').read_text(encoding='utf-8')
    meta_data = yaml.safe_load(meta_content)
    pages_path = Path(f"./output/publication/pages")
    pages_path.mkdir(exist_ok=True, parents=True)
    meta_info, work_id = get_meta_info(meta_data)
    meta_ttl = get_ttl(work_id)
    if meta_ttl != None:
        vol_info, num  = parse_volume_info(meta_ttl, work_id)
        if num != None:
            filename_info = get_file_name_info(vol_info, meta_info, num)
            meta_info = filename_info
    pages = get_pages(opf_path)
    Path(f"./output/vol_1.txt").write_text(pages['v001'], encoding='utf-8')
    change_file_name_pages(pages, pages_path, meta_info, False)
    create_zip(pages_path, f"{pecha_id}_pages.zip")
           

   
