# -*- coding: utf-8 -*-

'''
    Genesis Add-on
    Copyright (C) 2026 zeus768

    Donation dialog with QR code
'''

import xbmc
import xbmcgui
import xbmcaddon
import os
import time

try:
    import qrcode
    from io import BytesIO
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

DONATION_URL = 'https://ko-fi.com/zeus768'
DIALOG_TIMEOUT = 60  # 60 seconds timeout


class DonationDialog(xbmcgui.WindowXMLDialog):
    '''Custom dialog for showing donation QR code'''
    
    def __init__(self, *args, **kwargs):
        self.donation_url = kwargs.get('donation_url', DONATION_URL)
        self.timeout = kwargs.get('timeout', DIALOG_TIMEOUT)
        self.qr_image_path = None
        self.start_time = None
        self.timer_label = None
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)

    def onInit(self):
        self.start_time = time.time()
        self._generate_qr_code()
        self._start_countdown()

    def _generate_qr_code(self):
        '''Generate QR code image'''
        try:
            if HAS_QRCODE:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_M,
                    box_size=10,
                    border=4,
                )
                qr.add_data(self.donation_url)
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="black", back_color="white")
                
                # Save to addon data folder
                addon = xbmcaddon.Addon('plugin.video.genesis')
                addon_data = xbmc.translatePath(addon.getAddonInfo('profile'))
                if not os.path.exists(addon_data):
                    os.makedirs(addon_data)
                
                self.qr_image_path = os.path.join(addon_data, 'donation_qr.png')
                img.save(self.qr_image_path)
        except Exception as e:
            xbmc.log('[Genesis] Error generating QR code: %s' % str(e), xbmc.LOGERROR)

    def _start_countdown(self):
        '''Start the countdown timer'''
        while not self.isClosing():
            elapsed = time.time() - self.start_time
            remaining = max(0, self.timeout - int(elapsed))
            
            if remaining <= 0:
                self.close()
                break
            
            # Update countdown label if it exists
            try:
                self.getControl(1002).setLabel('Closing in %d seconds' % remaining)
            except:
                pass
            
            xbmc.sleep(1000)

    def isClosing(self):
        return not self.isOpen if hasattr(self, 'isOpen') else False

    def onClick(self, controlId):
        if controlId == 1003:  # Close button
            self.close()

    def onAction(self, action):
        if action.getId() in [xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK, 10]:
            self.close()


def show_donation_dialog():
    '''Show donation dialog with QR code - simplified version'''
    try:
        addon = xbmcaddon.Addon('plugin.video.genesis')
        addon_path = xbmc.translatePath(addon.getAddonInfo('path'))
        addon_data = xbmc.translatePath(addon.getAddonInfo('profile'))
        
        # Create a simple dialog
        dialog = xbmcgui.Dialog()
        
        # Generate QR code first if qrcode module is available
        qr_image_path = None
        if HAS_QRCODE:
            try:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_M,
                    box_size=10,
                    border=4,
                )
                qr.add_data(DONATION_URL)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                if not os.path.exists(addon_data):
                    os.makedirs(addon_data)
                qr_image_path = os.path.join(addon_data, 'donation_qr.png')
                img.save(qr_image_path)
            except Exception as e:
                xbmc.log('[Genesis] QR generation error: %s' % str(e), xbmc.LOGERROR)
        
        # Use fallback QR image if generation failed
        if not qr_image_path or not os.path.exists(qr_image_path):
            # Use pre-generated QR code from addon resources
            qr_image_path = os.path.join(addon_path, 'resources', 'skins', 'Default', 'media', 'qr_code.png')
        
        # Create window dialog with QR code
        show_qr_window(qr_image_path, DONATION_URL, DIALOG_TIMEOUT)
        
    except Exception as e:
        xbmc.log('[Genesis] Donation dialog error: %s' % str(e), xbmc.LOGERROR)
        # Fallback to simple dialog
        dialog = xbmcgui.Dialog()
        dialog.ok('Support Genesis', 
                  'Donate at: ' + DONATION_URL,
                  'Thank you for your support!')


def show_qr_window(qr_image_path, url, timeout):
    '''Show a custom window with QR code and countdown'''
    try:
        # Create a custom window
        window = QRWindow('DialogQR.xml', qr_image_path, url, timeout)
        window.doModal()
        del window
    except Exception as e:
        xbmc.log('[Genesis] QR window error: %s' % str(e), xbmc.LOGERROR)
        # Ultimate fallback
        remaining = timeout
        while remaining > 0:
            ret = xbmcgui.Dialog().yesno(
                'Buy Me a Beer! [COLOR yellow](%ds)[/COLOR]' % remaining,
                '[B]Support Genesis Development[/B]',
                '',
                'Scan QR or visit: [COLOR skyblue]%s[/COLOR]' % url,
                nolabel='Close',
                yeslabel='OK',
                autoclose=min(remaining * 1000, 10000)
            )
            if not ret:
                break
            remaining -= 10
            if remaining <= 0:
                break


class QRWindow(xbmcgui.WindowDialog):
    '''Simple window to display QR code with countdown'''
    
    def __init__(self, xml_file, qr_path, url, timeout):
        self.qr_path = qr_path
        self.url = url
        self.timeout = timeout
        self.start_time = time.time()
        self.running = True
        
        # Get screen dimensions
        self.width = 1920
        self.height = 1080
        
        # Create controls
        self._create_controls()
        
    def _create_controls(self):
        '''Create all window controls'''
        # Background
        self.background = xbmcgui.ControlImage(
            int(self.width * 0.25), int(self.height * 0.1),
            int(self.width * 0.5), int(self.height * 0.8),
            '', aspectRatio=0
        )
        self.addControl(self.background)
        self.background.setColorDiffuse('CC000000')  # Semi-transparent black
        
        # Title
        self.title = xbmcgui.ControlLabel(
            int(self.width * 0.25), int(self.height * 0.12),
            int(self.width * 0.5), 50,
            '[B][COLOR gold]Buy Me a Beer![/COLOR][/B]',
            alignment=0x00000002  # Center
        )
        self.addControl(self.title)
        
        # QR Code image
        if self.qr_path and os.path.exists(self.qr_path):
            self.qr_image = xbmcgui.ControlImage(
                int(self.width * 0.35), int(self.height * 0.2),
                int(self.width * 0.3), int(self.height * 0.45),
                self.qr_path, aspectRatio=2
            )
            self.addControl(self.qr_image)
        
        # URL label
        self.url_label = xbmcgui.ControlLabel(
            int(self.width * 0.25), int(self.height * 0.68),
            int(self.width * 0.5), 40,
            '[COLOR skyblue]%s[/COLOR]' % self.url,
            alignment=0x00000002
        )
        self.addControl(self.url_label)
        
        # Instructions
        self.instructions = xbmcgui.ControlLabel(
            int(self.width * 0.25), int(self.height * 0.73),
            int(self.width * 0.5), 30,
            'Scan QR code or visit the link above',
            alignment=0x00000002
        )
        self.addControl(self.instructions)
        
        # Countdown label
        self.countdown = xbmcgui.ControlLabel(
            int(self.width * 0.25), int(self.height * 0.78),
            int(self.width * 0.5), 30,
            '[COLOR yellow]Closing in %d seconds...[/COLOR]' % self.timeout,
            alignment=0x00000002
        )
        self.addControl(self.countdown)
        
        # Close instruction
        self.close_label = xbmcgui.ControlLabel(
            int(self.width * 0.25), int(self.height * 0.83),
            int(self.width * 0.5), 30,
            'Press [B]Back[/B] or [B]ESC[/B] to close',
            alignment=0x00000002
        )
        self.addControl(self.close_label)
        
        # Thank you message
        self.thanks = xbmcgui.ControlLabel(
            int(self.width * 0.25), int(self.height * 0.88),
            int(self.width * 0.5), 30,
            '[COLOR lime]Thank you for your support![/COLOR]',
            alignment=0x00000002
        )
        self.addControl(self.thanks)

    def doModal(self):
        '''Show window and start countdown'''
        self.show()
        self._countdown()
    
    def _countdown(self):
        '''Countdown timer loop'''
        while self.running:
            elapsed = time.time() - self.start_time
            remaining = max(0, self.timeout - int(elapsed))
            
            if remaining <= 0:
                self.close()
                break
            
            try:
                self.countdown.setLabel('[COLOR yellow]Closing in %d seconds...[/COLOR]' % remaining)
            except:
                pass
            
            xbmc.sleep(1000)
    
    def onAction(self, action):
        '''Handle user actions'''
        action_id = action.getId()
        # Back, escape, previous menu
        if action_id in [xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK, 10, 92]:
            self.running = False
            self.close()
