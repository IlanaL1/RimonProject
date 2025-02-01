### README

There are several parts to this
1. use appify - scrape FB groups - up to 500
2. use url_extraction.py to extract urls from JSON downloaded from appify (.json)
-- # input.json was output from appify 
-- # output of this file is external_links.md and facebook_links.md
3. The external files are in external_links.md
4. extract_url_from_md.py: Extract the urls from external_files.md

### Activate venv

### Aciviating venvv in PyCharm
cmd /k "activate"
To activate the venv1 cd venv1/scripts, the above
https://stackoverflow.com/questions/22288569/how-do-i-activate-a-virtualenv-inside-pycharms-terminal

Install the package
pip install -U crawl4ai

### Run post-installation setup
crawl4ai-setup

### Verify your installation
crawl4ai-doctor

Note - above passed in shell