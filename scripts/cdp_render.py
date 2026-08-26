# -*- coding: utf-8 -*-
"""M 型试点：用 CDP 渲染官方模型文档页，提取 innerText"""
import json
import time
import urllib.request
import websocket


def get_rendered(url, out, wait=14):
    tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json', timeout=10).read())
    page = next(t for t in tabs if t.get('type') == 'page')
    ws = websocket.create_connection(page['webSocketDebuggerUrl'], timeout=90)
    ws.send(json.dumps({'id': 10, 'method': 'Page.navigate', 'params': {'url': url}}))
    time.sleep(wait)
    ws.send(json.dumps({'id': 11, 'method': 'Runtime.evaluate',
                        'params': {'expression': 'document.body.innerText', 'returnByValue': True}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get('id') == 11:
            text = msg['result']['result'].get('value', '')
            break
    ws.close()
    with open(out, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f'{out}: {len(text)} chars')


if __name__ == '__main__':
    BASE = r'F:/project_temp/localAgent/workspace/model_data/raw_pages/'
    # Anthropic 官方模型对比页（含上下文窗口/多模态/定位描述）
    get_rendered('https://docs.claude.com/en/docs/about-claude/models/overview',
                 BASE + 'claude_models_overview.txt')
