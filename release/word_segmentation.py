import subprocess
from pathlib import Path
import pybo
import re




if __name__=="__main__":
    title = "བཀའ་འགྱུར། ༼ཕུག་བྲག་བྲིས་མ༽"
    title_output = subprocess.run(f"bo tok-string '{title}'", capture_output=True, shell=True, text=True)
    segmented_title = re.split(f"(\\\n)", title_output.stdout)
    title_done = segmented_title[2]
    print(title_done)
    Path(f"./input.txt").write_text(title_done, encoding='utf-8')
    subprocess.run('perl ./bin/pronounce.pl ./input.txt ./output.txt', shell=True)
    title = Path(f"./output.txt").read_text(encoding='utf-8')
    print(title)