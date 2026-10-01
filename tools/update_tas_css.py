import sys
import json
import base64
sys.path.append('tools')
import obs_client

# Precision CSS to hide the "Powered by TAS.gg" tab and shift badge flush to top
css = """
body {
    background-color: transparent !important;
    margin: 0px !important;
    padding: 0px !important;
    overflow: hidden !important;
}

/* Hide the top "Powered by TAS.gg" SVG tab entirely */
svg g[transform*="100 0"],
svg g[transform*="translate(100 0)"] {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
}

/* Shift the main badge up to remove the 22px gap left by the removed tab */
svg {
    transform: translateY(-22px);
    filter: drop-shadow(0 10px 24px rgba(0, 0, 0, 0.7));
}
"""

res = obs_client.call_obs('SetInputSettings', {
    'inputName': 'Twitch Apex Stats (Ranked)',
    'inputSettings': {'css': css},
    'overlay': True
})
print("Result:", res.get('d', {}).get('requestStatus'))

# Also capture screenshot to verify!
res_ss = obs_client.call_obs('GetSourceScreenshot', {
    'sourceName': 'GAMEPLAY ULTRA (Active)',
    'imageFormat': 'png',
    'imageWidth': 1920,
    'imageHeight': 1080
})
data = res_ss['d']['responseData']['imageData'].split(',', 1)[-1]
open('tas_css_test.png', 'wb').write(base64.b64decode(data))
print("Captured tas_css_test.png")
