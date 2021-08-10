import os
import shutil
from pathlib import Path
from botok.tokenizers import wordtokenizer
from git import Repo

config = {
    "OP_ORG": "https://github.com/Openpecha"
}

def clean_dir(layers_output_dir):
    if layers_output_dir.is_dir():
            shutil.rmtree(str(layers_output_dir))

def get_total_number_of_syllabus_in_pecha(pecha_id, pecha_path):
    sylsbus_len = 0
    base_path = f"{pecha_path}/{pecha_id}.opf/base/"
    for file in os.listdir(f"{base_path}"):
        if file.endswith(".txt"):
            file_name = file[:-4]
            base_text = Path(f"{base_path}/{file_name}.txt").read_text(encoding='utf-8')
            pre_processed = wordtokenizer.TokChunks(base_text, ignore_chars=None, space_as_punct=False)
            syls = pre_processed.get_syls()
            sylsbus_len += len(syls)
    return sylsbus_len

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
    print(f"{pecha_id} Downloaded ")
    return pecha_path

if __name__=="__main__":
    pecha_id = "P000511"
    file_path = "./"
    pecha_path = download_pecha(pecha_id, file_path)
    number_of_syllabus = get_total_number_of_syllabus_in_pecha(pecha_id, pecha_path)
    print(f" total number of syllabus is {number_of_syllabus}")
    clean_dir(pecha_path)
