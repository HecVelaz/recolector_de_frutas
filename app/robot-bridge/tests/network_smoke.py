"""Prueba real por socket; no escribe geocercas ni manda comandos."""
import asyncio
import json
import os
import urllib.request
from websockets.asyncio.client import connect


async def main():
    base = os.getenv('TEST_BRIDGE_URL', 'http://127.0.0.1:8001').rstrip('/')
    token = os.getenv('TEST_BRIDGE_TOKEN', '')
    headers = {'Authorization':f'Bearer {token}'}
    with urllib.request.urlopen(base + '/health', timeout=5) as response:
        health = json.load(response)
    assert health['service'] == 'arturito-bridge'
    with urllib.request.urlopen(urllib.request.Request(base + '/api/v1/telemetry', headers=headers), timeout=5) as response:
        first = json.load(response)
    url = base.replace('http://', 'ws://').replace('https://', 'wss://') + '/api/v1/telemetry'
    async with connect(url, additional_headers=headers) as ws:
        a = json.loads(await asyncio.wait_for(ws.recv(), 5))
        b = json.loads(await asyncio.wait_for(ws.recv(), 5))
    assert b['timestamp_ms'] > a['timestamp_ms']
    assert first['commands_enabled'] is False
    assert b['source'] == health['source']
    print('HTTP y WebSocket por socket: OK. Origen:', health['source'])


if __name__ == '__main__':
    asyncio.run(main())
