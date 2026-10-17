import csv
import html
import io
import json

def compare(before, after):
    if before['kind'] != after['kind']:
        raise ValueError('Compare two reports of the same analysis kind.')
    metrics=[]
    for key, value in after['metrics'].items():
        old=before['metrics'].get(key)
        if isinstance(value,(int,float)) and isinstance(old,(int,float)):
            metrics.append({'metric':key,'before':old,'after':value,'delta':round(value-old,4)})
    result={'before_id':before['id'],'after_id':after['id'],'kind':after['kind'],'score_delta':round(after['quality']['value']-before['quality']['value'],2),'metrics':metrics,'same_content':before['content_sha256']==after['content_sha256'],'same_engine':before['engine_version']==after['engine_version']}
    if after['kind']=='workflow':
        old={n['id']:n for n in before['graph']['nodes']};new={n['id']:n for n in after['graph']['nodes']}
        old_edges={(e['source'],e['target']) for e in before['graph']['edges']};new_edges={(e['source'],e['target']) for e in after['graph']['edges']}
        result['graph_changes']={'added_nodes':sorted(new.keys()-old.keys()),'removed_nodes':sorted(old.keys()-new.keys()),'changed_nodes':sorted(k for k in old.keys()&new.keys() if any(old[k].get(a)!=new[k].get(a) for a in ('label','type'))),'added_edges':[list(e) for e in sorted(new_edges-old_edges)],'removed_edges':[list(e) for e in sorted(old_edges-new_edges)]}
    return result

def csv_report(report):
    buffer=io.StringIO(newline='');writer=csv.writer(buffer)
    def safe(value):
        s=str(value)
        return "'"+s if s.lstrip().startswith(('=','+','-','@')) else s
    writer.writerow(['section','name','value'])
    for key in ['title','project','kind','engine_version','created_at','content_sha256']:
        writer.writerow(['metadata',key,safe(report.get(key,''))])
    for key,value in report['metrics'].items():writer.writerow(['metric',key,'' if value is None else value])
    writer.writerow(['quality','heuristic_score',report['quality']['value']])
    for penalty in report['quality']['penalties']:writer.writerow(['penalty',safe(penalty['label']),penalty['points']])
    for finding in report['findings']:writer.writerow(['finding',safe(finding['title']),safe(finding['detail'])])
    for unit in report['units']:writer.writerow(['scope_complexity',safe(unit['name']),unit['complexity']])
    return buffer.getvalue()

def html_report(report):
    esc=lambda value:html.escape(str(value))
    rows=''.join(f'<tr><th>{esc(k.replace("_"," "))}</th><td>{esc(v) if v is not None else "Not available"}</td></tr>' for k,v in report['metrics'].items())
    findings=''.join(f'<li><strong>{esc(x["title"])}</strong><p>{esc(x["detail"])}</p></li>' for x in report['findings']) or '<li>No configured structural hotspot rules were triggered.</li>'
    units=''.join(f'<tr><td>{esc(x["name"])}</td><td>{x["line"]}</td><td>{x["complexity"]}</td><td>{x["nesting"]}</td></tr>' for x in report['units'])
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>FlowScope report</title><style>body{{font:16px system-ui;max-width:900px;margin:48px auto;padding:0 24px;color:#152335}}h1,h2{{color:#153a38}}table{{border-collapse:collapse;width:100%;margin:20px 0}}th,td{{border:1px solid #cdd8d8;padding:10px;text-align:left}}p{{line-height:1.6}}@media print{{body{{margin:0}}}}</style><h1>{esc(report.get('title','Analysis report'))}</h1><p>Project {esc(report.get('project',''))} · {esc(report['kind'])} · {esc(report.get('created_at',''))}</p><h2>Heuristic review score {report['quality']['value']} / 100</h2><p>{esc(report['quality']['meaning'])}</p><h2>Measured structure</h2><table>{rows}</table><h2>Findings</h2><ul>{findings}</ul>{'<h2>Python scopes</h2><table><tr><th>Scope</th><th>Line</th><th>Complexity</th><th>Nesting</th></tr>'+units+'</table>' if units else ''}<h2>Score deductions</h2><ul>{''.join('<li>'+esc(p['label'])+': '+str(p['points'])+'</li>' for p in report['quality']['penalties']) or '<li>None</li>'}</ul><h2>Analysis limits</h2><ul>{''.join('<li>'+esc(w)+'</li>' for w in report['warnings'])}</ul><p>Engine {esc(report['engine_version'])}<br>Input SHA256 {esc(report['content_sha256'])}</p><p>See the FlowScope metric contract for formulas and interpretation. Use browser Print to save this report as PDF.</p></html>'''
