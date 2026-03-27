# -*- coding: utf-8 -*-
"""
QR Code Helper for Orion
Generates and displays QR codes for device pairing
"""

import xbmcgui
import xbmcaddon
import xbmcvfs
import urllib.request
import os

ADDON = xbmcaddon.Addon()

def generate_qr_url(data, size=300):
    """Generate QR code URL using external API"""
    import urllib.parse
    encoded_data = urllib.parse.quote(data)
    return f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={encoded_data}"

def download_qr_image(url, filename):
    """Download QR code image to temp directory"""
    temp_path = xbmcvfs.translatePath('special://temp/')
    file_path = os.path.join(temp_path, filename)
    
    try:
        headers = {'User-Agent': 'Orion/2.0'}
        req = urllib.request.Request(url, headers=headers)
        
        import ssl
        ctx = ssl._create_unverified_context()
        
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            with open(file_path, 'wb') as f:
                f.write(response.read())
        
        return file_path
    except Exception as e:
        return None

def show_qr(service_name, url):
    """Display QR code dialog for a service"""
    qr_url = generate_qr_url(url)
    qr_file = download_qr_image(qr_url, f"{service_name.lower()}_qr.png")
    
    if qr_file and xbmcvfs.exists(qr_file):
        # Create custom dialog with QR code
        dialog = QRDialog(service_name, url, qr_file)
        dialog.doModal()
        del dialog
    else:
        # Fallback to text dialog
        xbmcgui.Dialog().ok(
            f'{service_name} Authorization',
            f'Visit: [COLOR cyan]{url}[/COLOR]\n\n'
            'Scan the QR code or visit the URL above to authorize.'
        )

class QRDialog(xbmcgui.WindowDialog):
    """Custom dialog to display QR code"""
    
    def __init__(self, service_name, url, qr_image_path):
        super().__init__()
        
        # Get screen dimensions
        self.width = 1280
        self.height = 720
        
        # Dialog dimensions
        dialog_width = 600
        dialog_height = 550
        dialog_x = (self.width - dialog_width) // 2
        dialog_y = (self.height - dialog_height) // 2
        
        # Background
        self.background = xbmcgui.ControlImage(
            dialog_x, dialog_y, dialog_width, dialog_height,
            'special://xbmc/addons/skin.estuary/media/dialogs/dialog-bg.png'
        )
        self.addControl(self.background)
        
        # Title
        self.title = xbmcgui.ControlLabel(
            dialog_x, dialog_y + 20, dialog_width, 40,
            f'[B]{service_name} Authorization[/B]',
            alignment=2  # Center
        )
        self.addControl(self.title)
        
        # QR Code Image
        qr_size = 300
        qr_x = dialog_x + (dialog_width - qr_size) // 2
        qr_y = dialog_y + 70
        
        self.qr_image = xbmcgui.ControlImage(
            qr_x, qr_y, qr_size, qr_size,
            qr_image_path
        )
        self.addControl(self.qr_image)
        
        # URL Label
        self.url_label = xbmcgui.ControlLabel(
            dialog_x + 20, qr_y + qr_size + 20, dialog_width - 40, 30,
            f'[COLOR cyan]{url}[/COLOR]',
            alignment=2  # Center
        )
        self.addControl(self.url_label)
        
        # Instructions
        self.instructions = xbmcgui.ControlLabel(
            dialog_x + 20, qr_y + qr_size + 60, dialog_width - 40, 30,
            'Scan QR code or visit URL to authorize',
            alignment=2  # Center
        )
        self.addControl(self.instructions)
        
        # Close instruction
        self.close_label = xbmcgui.ControlLabel(
            dialog_x + 20, dialog_y + dialog_height - 50, dialog_width - 40, 30,
            '[COLOR gray]Press BACK to close[/COLOR]',
            alignment=2  # Center
        )
        self.addControl(self.close_label)
    
    def onAction(self, action):
        """Handle actions"""
        # Close on back/escape/select
        if action.getId() in [9, 10, 92, 7]:  # Back, Previous Menu, Backspace, Select
            self.close()