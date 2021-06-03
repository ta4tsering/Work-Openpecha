import re
from pathlib import Path
import yaml
from bs4 import BeautifulSoup
import xml.dom.minidom
from collections import defaultdict
from pyewts import pyewts

converter = pyewts()


def read_xml(xml):
    """
    The function returns xml content of transkribus output.
    
    Args:
        xml(.xml file): It is the output of Transkribus OCR model which contains the coordinates and text of
                        recognized box.
    Return:
        xml_content (String):It is the content of .xml file
    
    """
    with open(xml) as f:
        xml_content = f.read()
    return xml_content


def get_part(node):
    """Parse information of sections.

    Args:
        node (list): list of sections found

    Returns:
        dictionary: parsed information of each section with key as their RID
    """
    result = {}
    texts = node.find_all(["o:node", "outline:node"], recursive=False)
    for text in texts:
        rid = text["RID"]
        type_ = text.get("type")
        pg_start = ""
        pg_end = ""
        vol = ""
        if text.find_all(["o:name", "o:title", "outline:name", "outline:title"]):
            title = converter.toUnicode(
                text.find_all(["o:name", "o:title", "outline:name", "outline:title"])[0].string
            )
        else:
            title = ""
        locations = text.find_all(["o:location", "outline:location"], recursive=False)
        if locations:
            pg_start = locations[0].get("page", "")
            vol = locations[0].get("vol", "")
            if len(locations) > 1:
                pg_end = locations[1].get("page", "")
        child = get_part(text)
        result[rid] = {
            "title": re.sub("\n|\t", "", title),
            "type": type_,
            "pg_start": pg_start,
            "pg_end": pg_end,
            "vol": vol,
            "parts": child,
        }
    return result


def parse(xml):
    """Parse infromation such as rid, page_info, vol_info, work_id and sections of a text from
        outline output.

    Args:
        xml (str): outline output of ocred pecha

    Returns:
        dict: rid of text as key and parsed information as value
    """
    result = {}
    for node in nodes:
        rid = node["RID"]
        type_ = node["type"]
        pg_start = ""
        pg_end = ""
        vol = ""
        title = converter.toUnicode(
            node.find_all(["o:name", "o:title", "outline:name", "outline:title"])[0].string
        )
        locations = node.find_all(["o:location", "outline:location"], recursive=False)
        if locations:
            pg_start = locations[0].get("page", "")
            vol = locations[0].get("vol", "")
            if len(locations) > 1:
                pg_end = locations[1].get("page", "")
        parts = get_part(node)
        result[rid] = {
            "title": re.sub("\n|\t", "", title),
            "type": type_,
            "pg_start": pg_start,
            "pg_end": pg_end,
            "vol": vol,
            "parts": parts,
        }
    return result


if __name__ == "__main__":
    # input_path = Path('./egs-pretty')
    # input_pages = list(input_path.iterdir())
    # input_pages.sort()
    # for input_page in input_pages:
    #     xml = read_xml(input_page)
    #     print(f'{input_page.stem} Started..')
    #     soup = BeautifulSoup(xml, 'xml')
    #     outline = soup.find_all(["o:outline","outline:outline"])
    #     nodes = outline[0].find_all(["o:node","outline:node"], recursive=False)
    #     result = parse(nodes)
    #     result_yaml = yaml.safe_dump(result,default_flow_style=False, sort_keys=False,  allow_unicode=True)
    #     Path(f'./egs-output/{input_page.stem}.yaml').write_text(result_yaml, encoding='utf-8')
    #     print(f'{input_page.stem} done..')

    xml = read_xml("./derge-kangyur.xml")
    # dom = xml.dom.minidom.parse('./derge-kangyur.xml') # or xml.dom.minidom.parseString(xml_string)
    # xml = dom.toprettyxml()
    soup = BeautifulSoup(xml, "xml")
    outline = soup.find_all("outline:outline")
    nodes = outline[0].find_all("outline:node", recursive=False)
    result = parse(nodes)
    result_yaml = yaml.safe_dump(
        result, default_flow_style=False, sort_keys=False, allow_unicode=True
    )
    Path("./derge-kangyur.yaml").write_text(result_yaml, encoding="utf-8")
