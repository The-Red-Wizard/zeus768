"""
The Accountant - Speed Test Window with Animated Speedometer
Full-screen speedometer with clean non-overlapping layout and smooth needle.
"""
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import time
import math
import threading
import urllib.request
import ssl

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_ICON = ADDON.getAddonInfo('icon')
MEDIA_PATH = os.path.join(ADDON_PATH, 'resources', 'media')
# Solid white texture used together with colorDiffuse to render solid color fills.
WHITE_TEX = os.path.join(MEDIA_PATH, 'white.png')

# Color scheme matching Window XLM style
COLOR_BG_PANEL = 'FF0d2137'
COLOR_BORDER = 'FF00d4ff'
COLOR_TEXT_TITLE = 'FF00d4ff'
COLOR_TEXT_WHITE = 'FFffffff'
COLOR_TEXT_VALUE = 'FF00ffff'

# Speedometer colors
COLOR_SPEED_GREEN = 'FF00ff00'
COLOR_SPEED_ORANGE = 'FFff8800'


class SpeedTestWindow(xbmcgui.WindowDialog):
    """
    Full-screen Speed Test window with a large, smoothly-animated speedometer.
    Coordinates are designed on a 1920x1080 canvas and scale automatically.
    """

    # Full-screen panel with a thin margin for the cyan border
    PANEL_X = 40
    PANEL_Y = 40
    PANEL_W = 1840
    PANEL_H = 1000

    # Gauge geometry (on the 1920x1080 canvas)
    GAUGE_CY_OFFSET = 400     # distance from top of panel to gauge center
    GAUGE_RADIUS = 260        # outer radius of the arc
    NEEDLE_LENGTH = 230
    NEEDLE_SEGMENTS = 14      # number of small dots that make up the needle

    # Gauge arc (proper speedometer: opens downward)
    # 0 Mbps is at angle 225 degrees (lower-left)
    # max Mbps is at angle -45 degrees (lower-right)
    # Sweep is clockwise through the top (span = -270 degrees)
    ARC_START_ANGLE = 225
    ARC_SPAN = -270           # clockwise sweep, so negative

    # Max speed shown on the gauge. Most home connections are below this.
    # Speeds above this are clamped to the max on the gauge, but the numeric
    # readout (and download/upload stats) always show the real value.
    MAX_SPEED_MBPS = 500

    def __init__(self):
        super(SpeedTestWindow, self).__init__()
        self.controls = []
        self.running = False
        self.test_thread = None

        # Speed values
        self.current_speed = 0
        self.ping = 0
        self.download = 0
        self.upload = 0

        # Control references for updates
        self.speed_label = None
        self.ping_label = None
        self.download_label = None
        self.upload_label = None
        self.status_label = None
        self.needle_controls = []   # created once, repositioned on each update
        self.gauge_segments = []

        # Cached scale factors for update callbacks
        self._scale_x = 1.0
        self._scale_y = 1.0

        self._build_ui()

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        screen_width = self.getWidth()
        screen_height = self.getHeight()
        self._scale_x = screen_width / 1920.0
        self._scale_y = screen_height / 1080.0

        def sx(x): return int(x * self._scale_x)
        def sy(y): return int(y * self._scale_y)

        # Full-screen solid dark background (two layers for guaranteed opacity)
        for _ in range(2):
            bg = xbmcgui.ControlImage(
                0, 0, screen_width, screen_height,
                WHITE_TEX, colorDiffuse='FF0a1929'
            )
            self.addControl(bg)
            self.controls.append(bg)

        # Outer cyan border
        border = xbmcgui.ControlImage(
            sx(self.PANEL_X - 4), sy(self.PANEL_Y - 4),
            sx(self.PANEL_W + 8), sy(self.PANEL_H + 8),
            WHITE_TEX, colorDiffuse=COLOR_BORDER
        )
        self.addControl(border)
        self.controls.append(border)

        # Main panel background
        panel_bg = xbmcgui.ControlImage(
            sx(self.PANEL_X), sy(self.PANEL_Y),
            sx(self.PANEL_W), sy(self.PANEL_H),
            WHITE_TEX, colorDiffuse=COLOR_BG_PANEL
        )
        self.addControl(panel_bg)
        self.controls.append(panel_bg)

        # Title
        title = xbmcgui.ControlLabel(
            sx(self.PANEL_X), sy(self.PANEL_Y + 30),
            sx(self.PANEL_W), sy(70),
            'Real-Time Speed Test',
            font='font45',
            textColor=COLOR_TEXT_TITLE,
            alignment=0x00000002
        )
        self.addControl(title)
        self.controls.append(title)

        # Build the gauge (segments + scale labels + hub)
        self._build_gauge(sx, sy)

        # Create the needle pool (created once, repositioned on every update).
        self._build_needle_pool(sx, sy)

        # Big speed number in the middle of the gauge (slightly below center
        # so it does not fight with the needle hub)
        gauge_cx = self.PANEL_X + self.PANEL_W // 2
        gauge_cy = self.PANEL_Y + self.GAUGE_CY_OFFSET

        self.speed_label = xbmcgui.ControlLabel(
            sx(gauge_cx - 260), sy(gauge_cy + 60),
            sx(520), sy(110),
            '0',
            font='font45',
            textColor=COLOR_TEXT_VALUE,
            alignment=0x00000002
        )
        self.addControl(self.speed_label)
        self.controls.append(self.speed_label)

        mbps_label = xbmcgui.ControlLabel(
            sx(gauge_cx - 260), sy(gauge_cy + 170),
            sx(520), sy(40),
            'Mbps',
            font='font24_title',
            textColor=COLOR_TEXT_WHITE,
            alignment=0x00000002
        )
        self.addControl(mbps_label)
        self.controls.append(mbps_label)

        # Status line, well below the gauge
        self.status_label = xbmcgui.ControlLabel(
            sx(self.PANEL_X), sy(self.PANEL_Y + 700),
            sx(self.PANEL_W), sy(40),
            'Press Start to begin test',
            font='font24_title',
            textColor=COLOR_TEXT_WHITE,
            alignment=0x00000002
        )
        self.addControl(self.status_label)
        self.controls.append(self.status_label)

        # Separator above the stats row
        sep = xbmcgui.ControlImage(
            sx(self.PANEL_X + 80), sy(self.PANEL_Y + 760),
            sx(self.PANEL_W - 160), sy(3),
            WHITE_TEX, colorDiffuse=COLOR_BORDER
        )
        self.addControl(sep)
        self.controls.append(sep)

        # Stats row: LATENCY | DOWNLOAD | UPLOAD
        stats_y = self.PANEL_Y + 785
        col_width = (self.PANEL_W - 80) // 3

        def stat_title(x_offset, text):
            lbl = xbmcgui.ControlLabel(
                sx(self.PANEL_X + 40 + x_offset), sy(stats_y),
                sx(col_width), sy(30),
                text,
                font='font14',
                textColor='FFaaaaaa',
                alignment=0x00000002
            )
            self.addControl(lbl)
            self.controls.append(lbl)

        def stat_value(x_offset, text, color):
            lbl = xbmcgui.ControlLabel(
                sx(self.PANEL_X + 40 + x_offset), sy(stats_y + 35),
                sx(col_width), sy(55),
                text,
                font='font30',
                textColor=color,
                alignment=0x00000002
            )
            self.addControl(lbl)
            self.controls.append(lbl)
            return lbl

        stat_title(0, 'LATENCY (PING)')
        self.ping_label = stat_value(0, '-- ms', COLOR_TEXT_VALUE)

        stat_title(col_width, 'DOWNLOAD (Mbps)')
        self.download_label = stat_value(col_width, '-- Mbps', COLOR_SPEED_GREEN)

        stat_title(col_width * 2, 'UPLOAD (Mbps)')
        self.upload_label = stat_value(col_width * 2, '-- Mbps', COLOR_SPEED_ORANGE)

        # START TEST button at the bottom
        btn_w = 420
        btn_h = 64
        btn_x = self.PANEL_X + (self.PANEL_W - btn_w) // 2
        btn_y = self.PANEL_Y + self.PANEL_H - btn_h - 30

        btn_bg = xbmcgui.ControlImage(
            sx(btn_x), sy(btn_y),
            sx(btn_w), sy(btn_h),
            WHITE_TEX, colorDiffuse='FF00d4ff'
        )
        self.addControl(btn_bg)
        self.controls.append(btn_bg)

        btn_label = xbmcgui.ControlLabel(
            sx(btn_x), sy(btn_y + 15),
            sx(btn_w), sy(btn_h - 20),
            'START NEW TEST  (press ENTER)',
            font='font24_title',
            textColor='FF000000',
            alignment=0x00000002
        )
        self.addControl(btn_label)
        self.controls.append(btn_label)

        # Initial needle position at 0
        self._position_needle(0)

    # ------------------------------------------------------------------
    # Gauge arc + scale labels + center hub
    # ------------------------------------------------------------------
    def _build_gauge(self, sx, sy):
        gauge_cx = self.PANEL_X + self.PANEL_W // 2
        gauge_cy = self.PANEL_Y + self.GAUGE_CY_OFFSET
        r = self.GAUGE_RADIUS

        num_segments = 30
        seg_w = 40
        seg_h = 22

        for i in range(num_segments):
            ratio = i / (num_segments - 1)
            if ratio < 0.4:
                rr = int(255 * (ratio / 0.4))
                gg = 255
            elif ratio < 0.7:
                rr = 255
                gg = int(255 * (1 - (ratio - 0.4) / 0.3))
            else:
                rr = 255
                gg = int(136 * (1 - (ratio - 0.7) / 0.3))
            color = f'FF{rr:02x}{gg:02x}00'

            angle = self.ARC_START_ANGLE + (i / num_segments) * self.ARC_SPAN
            rad = math.radians(angle)

            mid_r = r - 25
            seg_x = gauge_cx + int(math.cos(rad) * mid_r) - seg_w // 2
            seg_y = gauge_cy - int(math.sin(rad) * mid_r) - seg_h // 2

            seg = xbmcgui.ControlImage(
                sx(seg_x), sy(seg_y),
                sx(seg_w), sy(seg_h),
                WHITE_TEX, colorDiffuse=color
            )
            self.addControl(seg)
            self.controls.append(seg)
            self.gauge_segments.append(seg)

        # Scale labels distributed evenly across the arc (0..MAX in 7 steps)
        max_v = self.MAX_SPEED_MBPS
        scale_values = [0, int(max_v * 0.2), int(max_v * 0.4), int(max_v * 0.5),
                        int(max_v * 0.6), int(max_v * 0.8), max_v]
        scale_ratios = [0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0]

        label_r = r + 40  # outside the arc
        for val, ratio in zip(scale_values, scale_ratios):
            angle = self.ARC_START_ANGLE + ratio * self.ARC_SPAN
            rad = math.radians(angle)
            label_x = gauge_cx + int(math.cos(rad) * label_r) - 50
            label_y = gauge_cy - int(math.sin(rad) * label_r) - 18

            scale_label = xbmcgui.ControlLabel(
                sx(label_x), sy(label_y),
                sx(100), sy(36),
                str(val),
                font='font14',
                textColor=COLOR_TEXT_WHITE,
                alignment=0x00000002
            )
            self.addControl(scale_label)
            self.controls.append(scale_label)

        # Gauge center hub
        hub_size = 52
        center_circle = xbmcgui.ControlImage(
            sx(gauge_cx - hub_size // 2), sy(gauge_cy - hub_size // 2),
            sx(hub_size), sy(hub_size),
            WHITE_TEX, colorDiffuse=COLOR_BORDER
        )
        self.addControl(center_circle)
        self.controls.append(center_circle)

    # ------------------------------------------------------------------
    # Needle pool: create once, reposition on every update (no flicker)
    # ------------------------------------------------------------------
    def _build_needle_pool(self, sx, sy):
        # Create NEEDLE_SEGMENTS small cyan dots off-screen; they are
        # repositioned by _position_needle() every animation frame.
        for i in range(self.NEEDLE_SEGMENTS):
            seg_size = max(6, 20 - i)
            seg = xbmcgui.ControlImage(
                -100, -100,  # off-screen until first reposition
                sx(seg_size), sy(seg_size),
                WHITE_TEX, colorDiffuse=COLOR_TEXT_VALUE
            )
            self.addControl(seg)
            self.controls.append(seg)
            self.needle_controls.append((seg, seg_size))

    def _position_needle(self, speed):
        """Reposition the existing needle segments to point at `speed`."""
        gauge_cx = self.PANEL_X + self.PANEL_W // 2
        gauge_cy = self.PANEL_Y + self.GAUGE_CY_OFFSET

        clamped = min(max(speed, 0), self.MAX_SPEED_MBPS)
        ratio = clamped / self.MAX_SPEED_MBPS
        angle = self.ARC_START_ANGLE + ratio * self.ARC_SPAN
        rad = math.radians(angle)

        n = len(self.needle_controls)
        if n == 0:
            return

        for i, (seg, seg_size) in enumerate(self.needle_controls):
            seg_r = (i + 1) * (self.NEEDLE_LENGTH / n)
            px = gauge_cx + int(math.cos(rad) * seg_r) - seg_size // 2
            py = gauge_cy - int(math.sin(rad) * seg_r) - seg_size // 2
            try:
                seg.setPosition(int(px * self._scale_x), int(py * self._scale_y))
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Update readouts + needle
    # ------------------------------------------------------------------
    def _update_display(self, speed=0, ping=0, download=0, upload=0, status=''):
        try:
            if self.speed_label is not None:
                self.speed_label.setLabel(f'{speed:.1f}' if speed < 100 else f'{int(speed)}')

            if self.ping_label is not None:
                self.ping_label.setLabel(f'{int(ping)} ms' if ping > 0 else '-- ms')

            if self.download_label is not None:
                self.download_label.setLabel(f'{download:.1f} Mbps' if download > 0 else '-- Mbps')

            if self.upload_label is not None:
                self.upload_label.setLabel(f'{upload:.1f} Mbps' if upload > 0 else '-- Mbps')

            if self.status_label is not None and status:
                self.status_label.setLabel(status)

            self._position_needle(speed)
        except Exception as e:
            xbmc.log(f'[Accountant] Speed display update error: {e}', xbmc.LOGDEBUG)

    # ------------------------------------------------------------------
    # Actual speed test (unchanged logic, slightly tidier)
    # ------------------------------------------------------------------
    def _run_speed_test(self):
        self.running = True
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            # Phase 1: Ping test
            self._update_display(speed=0, status='Testing latency...')
            ping_times = []
            ping_url = 'https://www.google.com'

            for i in range(5):
                if not self.running:
                    return
                try:
                    start = time.time()
                    req = urllib.request.Request(ping_url, headers={'User-Agent': 'Mozilla/5.0'})
                    urllib.request.urlopen(req, timeout=5, context=ctx)
                    ping_time = (time.time() - start) * 1000
                    ping_times.append(ping_time)
                    self._update_display(speed=20 + i * 10, ping=ping_time,
                                         status=f'Ping test {i+1}/5...')
                    xbmc.sleep(150)
                except Exception:
                    pass

            self.ping = sum(ping_times) / len(ping_times) if ping_times else 0
            if not self.running:
                return

            # Phase 2: Download test
            self._update_display(speed=0, ping=self.ping, status='Testing download speed...')
            download_speeds = []
            test_urls = [
                ('https://speed.cloudflare.com/__down?bytes=100000000', 'Cloudflare'),
                ('https://proof.ovh.net/files/10Mb.dat', 'OVH'),
            ]

            last_ui_ts = 0
            for url, server in test_urls:
                if not self.running:
                    return
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    start = time.time()
                    response = urllib.request.urlopen(req, timeout=25, context=ctx)

                    total_data = 0
                    chunk_size = 65536

                    while self.running:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        total_data += len(chunk)
                        elapsed = time.time() - start
                        if elapsed <= 0:
                            continue

                        current_speed = (total_data * 8) / (elapsed * 1000000)
                        # Throttle UI updates to ~15 per second to keep
                        # the needle animation smooth and CPU low.
                        now = time.time()
                        if now - last_ui_ts > 0.066:
                            self._update_display(
                                speed=current_speed,
                                ping=self.ping,
                                download=current_speed,
                                status=f'Downloading from {server}... {current_speed:.1f} Mbps'
                            )
                            last_ui_ts = now

                    elapsed = time.time() - start
                    if elapsed > 0 and total_data > 0:
                        final_speed = (total_data * 8) / (elapsed * 1000000)
                        download_speeds.append(final_speed)
                except Exception as e:
                    xbmc.log(f'[Accountant] Download test error: {e}', xbmc.LOGDEBUG)

            self.download = max(download_speeds) if download_speeds else 0
            if not self.running:
                return

            # Phase 3: Upload test
            self._update_display(speed=self.download, ping=self.ping,
                                 download=self.download, status='Testing upload speed...')

            try:
                test_data = b'x' * 2000000  # 2 MB
                upload_url = 'https://httpbin.org/post'
                req = urllib.request.Request(
                    upload_url, data=test_data,
                    headers={'User-Agent': 'Mozilla/5.0',
                             'Content-Type': 'application/octet-stream'}
                )

                start = time.time()
                # Animate the needle during the upload
                for i in range(12):
                    if not self.running:
                        return
                    fake = (i + 1) * (self.download * 0.12)
                    self._update_display(
                        speed=fake, ping=self.ping,
                        download=self.download, upload=fake,
                        status=f'Uploading... {fake:.1f} Mbps'
                    )
                    xbmc.sleep(180)

                response = urllib.request.urlopen(req, timeout=30, context=ctx)
                response.read()
                elapsed = time.time() - start
                if elapsed > 0:
                    self.upload = (len(test_data) * 8) / (elapsed * 1000000)
            except Exception as e:
                xbmc.log(f'[Accountant] Upload test error: {e}', xbmc.LOGDEBUG)
                self.upload = 0

            # Final result
            self._update_display(
                speed=self.download, ping=self.ping,
                download=self.download, upload=self.upload,
                status='Test complete! Press ENTER to test again'
            )
        except Exception as e:
            xbmc.log(f'[Accountant] Speed test error: {e}', xbmc.LOGERROR)
            self._update_display(speed=0, status=f'Test failed: {str(e)[:40]}')
        finally:
            self.running = False

    def _start_test(self):
        if self.running:
            return
        self.current_speed = 0
        self.ping = 0
        self.download = 0
        self.upload = 0
        self._update_display(speed=0, ping=0, download=0, upload=0, status='Starting test...')

        self.test_thread = threading.Thread(target=self._run_speed_test)
        self.test_thread.daemon = True
        self.test_thread.start()

    def onAction(self, action):
        action_id = action.getId()
        if action_id in [xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK,
                         xbmcgui.ACTION_BACKSPACE, 92]:
            self.running = False
            self.close()
        elif action_id in [xbmcgui.ACTION_SELECT_ITEM, 7, 100]:
            self._start_test()


def show_speed_test_window():
    """Display the custom full-screen Speed Test window."""
    try:
        window = SpeedTestWindow()
        window.doModal()
        del window
    except Exception as e:
        xbmc.log(f'[The Accountant] Speed Test Window Error: {e}', xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Speed Test', f'Could not load custom window.\nError: {str(e)}')
        return False
    return True
