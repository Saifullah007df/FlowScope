"""Single-user, loopback-only API and static console."""
import asyncio
import json
import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware
from .analysis import analyze, AnalysisError, ENGINE_VERSION
from .storage import Store
from .reports import compare, csv_report, html_report

ROOT=Path(__file__).resolve().parent.parent
class AnalysisRequest(BaseModel):
    title: str=Field(default='Untitled analysis', min_length=1, max_length=120)
    project: str=Field(default='My workspace', min_length=1, max_length=80)
    kind: Literal['auto','workflow','python']='auto'
    content: str=Field(min_length=1,max_length=1_000_000)

class BodyLimit:
    def __init__(self,app): self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or scope['method'] not in {'POST','PUT','PATCH'}:
            return await self.app(scope,receive,send)
        parts=[];size=0
        while True:
            message=await receive()
            if message['type']=='http.disconnect':return
            part=message.get('body',b'');size+=len(part)
            if size>2_000_000:
                return await JSONResponse({'detail':'Request body exceeds 2 MB.'},status_code=413)(scope,receive,send)
            parts.append(part)
            if not message.get('more_body'):break
        sent=False
        async def replay():
            nonlocal sent
            if not sent:
                sent=True;return {'type':'http.request','body':b''.join(parts),'more_body':False}
            return await receive()
        await self.app(scope,replay,send)

def create_app(db_path=None):
    app=FastAPI(title='FlowScope',version=ENGINE_VERSION)
    store=Store(db_path or os.environ.get('FLOWSCOPE_DB',str(ROOT/'runtime'/'history.sqlite3')))
    app.state.store=store
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','[::1]','testserver'])
    app.add_middleware(BodyLimit)
    @app.middleware('http')
    async def protect(request:Request,call_next):
        if request.method in {'POST','DELETE','PUT','PATCH'}:
            origin=request.headers.get('origin')
            if origin and (urlparse(origin).netloc != request.headers.get('host') or urlparse(origin).scheme not in {'http','https'}):
                return JSONResponse({'detail':'Cross-origin changes are not allowed.'},status_code=403)
            if request.headers.get('sec-fetch-site')=='cross-site':
                return JSONResponse({'detail':'Cross-site changes are not allowed.'},status_code=403)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        response.headers['Cache-Control']='no-store'
        return response
    def get_report(report_id):
        result=store.get(report_id)
        if not result: raise HTTPException(404,'Report not found.')
        return result
    @app.get('/api/health')
    def health(): return {'status':'ok','engine_version':ENGINE_VERSION}
    @app.get('/api/examples')
    def examples():
        return [{'name':p.stem.replace('-',' ').title(),'filename':p.name,'kind':'python' if p.suffix=='.py' else 'workflow','content':p.read_text()} for p in sorted((ROOT/'examples').iterdir()) if p.suffix in {'.py','.json'}]
    @app.post('/api/analyze',status_code=201)
    def run(payload:AnalysisRequest):
        title=payload.title.strip();project=payload.project.strip()
        if not title or not project:raise HTTPException(422,'Title and project cannot be blank.')
        try:result=analyze(payload.content,payload.kind)
        except AnalysisError as exc:raise HTTPException(422,str(exc)) from None
        return store.save(result,title,project)
    @app.get('/api/reports')
    def history():return store.list()
    @app.get('/api/reports/{report_id}')
    def report(report_id:str):return get_report(report_id)
    @app.delete('/api/reports/{report_id}',status_code=204)
    def delete(report_id:str):
        if not store.delete(report_id):raise HTTPException(404,'Report not found.')
        return Response(status_code=204)
    @app.get('/api/compare')
    def comparison(before:str,after:str):
        try:return compare(get_report(before),get_report(after))
        except ValueError as exc:raise HTTPException(422,str(exc)) from None
    @app.get('/api/reports/{report_id}/export/{format}')
    def export(report_id:str,format:str):
        record=get_report(report_id)
        if format=='json':content=json.dumps(record,indent=2,ensure_ascii=False);media='application/json'
        elif format=='csv':content=csv_report(record);media='text/csv'
        elif format=='html':content=html_report(record);media='text/html'
        else:raise HTTPException(404,'Supported formats are json, csv and html.')
        return Response(content,media_type=media,headers={'Content-Disposition':f'attachment; filename="flowscope-{report_id[:8]}.{format}"'})
    @app.get('/api/methodology')
    def methodology():return {'markdown':(ROOT/'docs'/'metric-contract.md').read_text()}
    @app.get('/')
    def home():return FileResponse(ROOT/'web'/'index.html')
    app.mount('/assets',StaticFiles(directory=ROOT/'web'),name='assets')
    return app
