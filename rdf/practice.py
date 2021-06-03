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


def check_locationstatement(g, pg_list):
    final = pg_list
    for pg in pg_list:
        locations = g.objects(BDR[pg], BDO["contentLocationStatement"])
        try:
            for location in locations:
                loc_id = get_id(str(location))
        except:

        
        


def get_list(g, _id):
    pg_ids = []
    pgs = g.objects(BDR[_id], BDO["hasPart"])
    for pg in pgs:
        pg_id = get_id(str(pg))
        pg_ids.append(pg_id)
    return pg_ids

def check_haspart(g, _id):
    pgs = g.objects(BDR[_id], BDO["hasPart"])
    if len(list(pgs)) != 0:
        pg_ids = get_list(g, _id)
        return True, pg_ids
    else:
        pgs = g.objects(BDR[_id], BDO["partOf"])
        for pg in pgs:
            pg_id = get_id(str(pg))
        return False, pg_id

def get_pg_ids_without_haspart(g, _id):
    pg_ids = []
    res, pgs = check_haspart(g, _id)
    if res == True:
        pg_ids = get_pg_ids_without_haspart(g, pgs[0])
        return pg_ids
    elif res == False:
        pg_ids = get_list(g, pgs)
        return pg_ids


def parse_ttl_info(meta_ttl, work_id):
    pg_list = []
    work_id = f"M{work_id}"
    g = Graph()
    try:
        g.parse(data=meta_ttl, format="ttl")
    except:
        logging.warning(f"{work_id}.ttl Contains bad syntax")
        return {}
    parts = g.objects(BDR[work_id], BDO["hasPart"])
    for part in parts:
        pg_id = get_id(str(part))
        pg_ids = get_pg_ids_without_haspart(g, pg_id)
        for pg in pg_ids:
            pg_list.append(pg)
    final_list = check_locationstatement(g, pg_list)
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

if __name__=='__main__':
    work_id = "W21809"
    meta_ttl = get_ttl(work_id)
    pagination_info  = parse_ttl_info(meta_ttl, work_id)
    
    