import os 
import re
import yaml
from zipfile36 import ZipFile
from os.path import basename
from pathlib import Path
from openpecha.serializers import HFMLSerializer

def get_meta_info(meta_data):
    volumes = meta_data['vol2fn']
    cur_text = {}
    meta_info = {}
    num = 1
    for vol_num, image_group in volumes.items():
        image_group = volumes[vol_num][1:-4]
        cur_text[num] = { 
            'image_group': image_group,
            'vol_num': vol_num,
        }
        meta_info.update(cur_text)
        num += 1
        cur_text = {}
    return meta_info

def change_file_name_pages(pages, pages_path, meta_info):
    _type = "pages"
    for num, vol_num in enumerate(pages,1):
        for info_num, meta in meta_info.items():
            meta_vol = meta['vol_num']
            if meta_vol == vol_num:
                content = pages[f'{vol_num}']
                lines = re.split(f"(\\\n)", content)
                pages_content = get_clean_pages(lines, meta_info, vol_num)
                write_text(pages_content, pages_path, vol_num, _type)
                break
               
def change_file_name_plain(meta_info, opf_path, new_path):
    _type = "plain"
    for file in os.listdir(f"{opf_path}/base"):
        if file.endswith(".txt"):
            file_path = Path(f"{opf_path}/base/{file}")
            file_name = file[1:-4]
            content = Path(f'{file_path}').read_text(encoding='utf-8')
            for info_num, meta in meta_info.items():
                vol = meta['vol_num']
                new_vol = vol[1:]
                if new_vol == file_name:
                    vol_num = file_name
                    write_text(content, new_path, vol_num, _type)    
                    break

def create_zip(base_path, name):
    with ZipFile(name, 'w') as zipObj:
        for folderName, subfolders, filenames in os.walk(base_path):
            for filename in filenames:
                filePath = os.path.join(folderName, filename)
                zipObj.write(filePath, basename(filePath))

def erase_page_index(new_content, meta_info, vol_num):
    new_line = []
    new_page = ""
    lines = re.split(f"(\\\n)", new_content)
    for num, meta in meta_info.items():
        meta_num = meta['vol_num']
        if vol_num == meta_num:
            image_group = meta['image_group']
            for num, line in enumerate(lines,1):
                if re.match(f"\s({image_group}\_)", line):
                    new_line = re.sub(f"\s({image_group}\_)", "", line )
                    if new_line != '':
                        img_num = int(new_line)
                        new_page += f" i-{img_num}"
                        new_line = []
                elif re.match(f"(\\\n)", line):
                    new_page += "\n"
                elif line != '':
                    new_page += line
    return new_page

def get_clean_pages(lines, meta_info, vol_num):
    new_line = []
    new_content = ""
    for num, line in enumerate(lines,1):
        if  num % 2 != 0:
            new_line = re.sub(f"(\[((.\d+\w)|(\d+(a|b)\.\d+)|(\.\d+))\])", "", line )
            new_content += new_line
            new_line = []
        else:
            new_content += "\n"
    new_content = erase_page_index(new_content, meta_info, vol_num)
    return new_content

def write_text(content, new_path, vol_num, _type):
    out_fn = Path(f"{new_path}/{vol_num}_{_type}.txt")
    out_fn.write_text(content, encoding='utf-8')


if __name__=="__main__":
    pecha_id = 'P000789'
    opf_path = Path(f'./{pecha_id}/{pecha_id}.opf')
    meta_content = Path(f'./{pecha_id}/{pecha_id}.opf/meta.yml').read_text(encoding='utf-8')
    meta_data = yaml.safe_load(meta_content)
    # base_path = Path(f'{opf_path}/base')
    # plain_path = Path(f"./output/publication/plains")
    # plain_path.mkdir(exist_ok=True, parents=True)
    meta_info = get_meta_info(meta_data)
    # change_file_name_plain(meta_info, opf_path, plain_path) 
    # create_zip(plain_path, f"{pecha_id}_plain.zip")
    pages_path = Path(f"./output/publication/pages")
    pages_path.mkdir(exist_ok=True, parents=True)
    serializer = HFMLSerializer(opf_path, layers=["Pagination"])
    serializer.apply_layers()
    pages = serializer.get_result()
    change_file_name_pages(pages, pages_path, meta_info)
    create_zip(pages_path, f"{pecha_id}_pages.zip")
