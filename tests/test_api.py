import csv
import io
import json
import subprocess
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from flowscope.api import create_app
from flowscope.storage import Store

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path/'history.sqlite3')) as c:yield c

def create(client,content='def f():\n    return 1\n',**kwargs):
    return client.post('/api/analyze',json={'content':content,**kwargs})

def test_journey_history_restart_compare_exports(tmp_path):
    path=tmp_path/'history.sqlite3'
    with TestClient(create_app(path)) as client:
        assert client.get('/').status_code==200
        assert client.get('/assets/app.js').status_code==200
        assert len(client.get('/api/examples').json())==4
        a=create(client,title='First',project='Demo').json()
        b=create(client,'def f(x):\n    if x: return 1\n    return 0',title='Second',project='Demo').json()
        assert len(client.get('/api/reports').json())==2
        diff=client.get('/api/compare',params={'before':a['id'],'after':b['id']}).json()
        assert next(m for m in diff['metrics'] if m['metric']=='decision_count')['delta']==1
        for format in ['json','csv','html']:
            response=client.get(f'/api/reports/{b["id"]}/export/{format}')
            assert response.status_code==200 and 'attachment' in response.headers['content-disposition']
        assert 'content' not in a
    with TestClient(create_app(path)) as client:
        assert client.get('/api/reports/'+a['id']).json()['title']=='First'
        assert client.delete('/api/reports/'+a['id']).status_code==204
        assert client.get('/api/reports/'+a['id']).status_code==404

def test_graph_diff_and_kind_rejection(client):
    a=create(client,'{"nodes":[{"id":"a"}]}').json()
    b=create(client,'{"nodes":[{"id":"a","next":["b"]},{"id":"b"}]}').json()
    result=client.get('/api/compare',params={'before':a['id'],'after':b['id']}).json()
    assert result['graph_changes']['added_nodes']==['b']
    assert result['graph_changes']['added_edges']==[['a','b']]
    c=create(client).json()
    assert client.get('/api/compare',params={'before':a['id'],'after':c['id']}).status_code==422

def test_validation_and_origin_protection(client):
    assert create(client,'{"nodes":[{"id":"a","next":["missing"]}]}').status_code==422
    assert create(client,kind='java').status_code==422
    assert create(client,title='   ').status_code==422
    assert client.post('/api/analyze',headers={'Origin':'https://evil.example'},json={'content':'x=1'}).status_code==403
    assert client.get('/api/health',headers={'Host':'evil.example'}).status_code==400
    assert client.get('/api/health').headers['x-content-type-options']=='nosniff'
    assert client.post('/api/analyze',content=b'x'*2_000_001,headers={'Content-Type':'application/json'}).status_code==413

def test_export_escaping_and_csv_formula_safety(client):
    a=create(client,'{"nodes":[{"id":"a","name":"<script>alert(1)</script>"}]}',title='=HYPERLINK("evil")',project='<script>bad</script>').json()
    html=client.get(f'/api/reports/{a["id"]}/export/html').text
    assert '<script>' not in html
    assert '&lt;script&gt;' in html
    rows=list(csv.reader(io.StringIO(client.get(f'/api/reports/{a["id"]}/export/csv').text)))
    assert next(r for r in rows if r[1]=='title')[2].startswith("'=")

def test_retention_and_source_absence(client):
    a=create(client,'secret_source_marker=42').json()
    assert 'secret_source_marker' not in json.dumps(a)
    assert client.get('/api/reports/'+a['id']+'/export/xml').status_code==404

def test_cli_exit_codes(tmp_path):
    source=tmp_path/'source.py';source.write_text('x=1')
    command=[sys.executable,'-m','flowscope',str(source)]
    a=subprocess.run(command,capture_output=True,text=True)
    assert a.returncode==0 and json.loads(a.stdout)['kind']=='python'
    assert subprocess.run(command+['--fail-score-below','101'],capture_output=True).returncode==1
    source.write_text('def !!!')
    assert subprocess.run(command,capture_output=True).returncode==2


def test_history_retains_latest_200(tmp_path):
    store=Store(tmp_path/'history.sqlite3')
    report={'kind':'python','quality':{'value':100}}
    first=store.save(report,'First','Retention')
    for i in range(200): store.save(report,str(i),'Retention')
    assert len(store.list())==200
    assert store.get(first['id']) is None
