import sys
import time
import json
import asyncio
import aiohttp
import base64
sys.path.append('tools')
import obs_client

async def simulate_movement():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect('http://127.0.0.1:8998/ws') as ws:
            print("Connected to input daemon. Simulating neo-strafe + tap-strafe + superglide sequence...")

            # 1. Neo-strafe rapid circular pattern: A -> S -> D -> W + Crouch spam
            keys = ['A', 'S', 'D', 'W', 'CROUCH', 'A', 'S', 'D', 'W', 'CROUCH']
            for k in keys:
                await ws.send_str(json.dumps({"type": "key", "name": k, "down": True}))
                await asyncio.sleep(0.04)
                await ws.send_str(json.dumps({"type": "key", "name": k, "down": False}))
                await asyncio.sleep(0.02)

            # 2. Tap-strafe rapid scroll wheel up burst (5 ticks)
            for _ in range(5):
                await ws.send_str(json.dumps({"type": "wheel", "dir": "up"}))
                await asyncio.sleep(0.02)

            # 3. Superglide: Jump + Crouch struck simultaneously!
            await ws.send_str(json.dumps({"type": "key", "name": "JUMP", "down": True}))
            await ws.send_str(json.dumps({"type": "key", "name": "CROUCH", "down": True}))
            await ws.send_str(json.dumps({"type": "key", "name": "W", "down": True}))
            await ws.send_str(json.dumps({"type": "wheel", "dir": "up"}))

            # Keep keys active while screenshot is taken!
            await asyncio.sleep(0.1)

            # Capture OBS screenshot
            res = obs_client.call_obs('GetSourceScreenshot', {
                'sourceName': 'GAMEPLAY ULTRA (Active)',
                'imageFormat': 'png',
                'imageWidth': 1920,
                'imageHeight': 1080
            })
            if res.get('d', {}).get('requestStatus', {}).get('result'):
                img_data = res['d']['responseData']['imageData'].split(',', 1)[-1]
                with open('neostrafe_live_test.png', 'wb') as f:
                    f.write(base64.b64decode(img_data))
                print("Saved neostrafe_live_test.png successfully during active movement!")

            # Release keys
            await asyncio.sleep(0.2)
            await ws.send_str(json.dumps({"type": "key", "name": "JUMP", "down": False}))
            await ws.send_str(json.dumps({"type": "key", "name": "CROUCH", "down": False}))
            await ws.send_str(json.dumps({"type": "key", "name": "W", "down": False}))

asyncio.run(simulate_movement())
