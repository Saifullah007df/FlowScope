"""Static client/server integration checks; not a substitute for browser QA."""
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
class Page(HTMLParser):
    def __init__(self):
        super().__init__();self.ids=[];self.assets=[];self.labels=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if tag=='label' and 'for' in a:self.labels.append(a['for'])
        if tag=='script' and 'src' in a:self.assets.append(a['src'])
        if tag=='link' and a.get('rel')=='stylesheet':self.assets.append(a['href'])

def test_console_element_and_asset_contract():
    page=Page();page.feed((ROOT/'web/index.html').read_text())
    assert len(page.ids)==len(set(page.ids))
    references=set(re.findall(r"\$\('([^']+)'\)",(ROOT/'web/app.js').read_text()))
    assert references.issubset(page.ids)
    assert set(page.labels).issubset(page.ids)
    for asset in page.assets:
        assert asset.startswith('/assets/')
        assert (ROOT/'web'/asset.removeprefix('/assets/')).is_file()
    assert 'innerHTML' not in (ROOT/'web/app.js').read_text()
