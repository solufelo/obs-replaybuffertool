import sys
sys.path.append('tools')
import obs_client

original_css = """
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
    'inputSettings': {
        'url': 'https://overlays.tas.gg/217857230/98130/rp-games-nextrank-cycle',
        'is_local_file': False,
        'width': 550,
        'height': 160,
        'css': original_css
    }
})
print('Restored TAS.gg Apex Stats overlay:', res)

obs_client.call_obs('PressInputPropertiesButton', {
    'inputName': 'Twitch Apex Stats (Ranked)',
    'propertyName': 'refreshnocache'
})
print('Refreshed source')
