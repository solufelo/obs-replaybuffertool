import sys
import base64
sys.path.append('tools')
import obs_client

out_path = sys.argv[1] if len(sys.argv) > 1 else 'obs_capture.png'
scene_name = sys.argv[2] if len(sys.argv) > 2 else 'GAMEPLAY ULTRA (Active)'

res = obs_client.call_obs('GetSourceScreenshot', {
    'sourceName': scene_name,
    'imageFormat': 'png',
    'imageWidth': 1920,
    'imageHeight': 1080
})

if res.get('d', {}).get('requestStatus', {}).get('result'):
    img_data = res['d']['responseData']['imageData'].split(',', 1)[-1]
    with open(out_path, 'wb') as f:
        f.write(base64.b64decode(img_data))
    print(f"Saved {out_path}")
else:
    print(f"Error capturing: {res}")
