"""
The Accountant - Custom Account Cards Window
Full-screen programmatic window with solid backgrounds.
Uses each service's own icon and displays the addon icon on the right.
"""
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_ICON = ADDON.getAddonInfo('icon')
MEDIA_PATH = os.path.join(ADDON_PATH, 'resources', 'media')
# Solid white texture used together with colorDiffuse to render solid color fills.
# Without a real texture, colorDiffuse has nothing to tint -> result is transparent.
WHITE_TEX = os.path.join(MEDIA_PATH, 'white.png')

# Color scheme matching Window XLM style
COLOR_BG_DARK = '0xFF0a1929'       # Dark blue background
COLOR_BG_PANEL = '0xFF0d2137'      # Panel background (solid dark blue-purple)
COLOR_BORDER = '0xFF00d4ff'        # Cyan border/accent
COLOR_TEXT_TITLE = '0xFF00d4ff'    # Cyan for titles
COLOR_TEXT_STATUS_OK = '0xFF00ff00'    # Green for authorized
COLOR_TEXT_STATUS_ERR = '0xFFff3333'   # Red for not authorized
COLOR_TEXT_WHITE = '0xFFffffff'    # White text
COLOR_ROW_BG = '0xFF13304f'        # Solid row background (slightly lighter than panel)


class AccountCardsWindow(xbmcgui.WindowDialog):
    """
    Full-screen custom window for displaying Account Cards
    (dark blue background, cyan accents, addon icon on the right).
    Coordinates are designed on a 1920x1080 canvas and scale automatically.
    """

    # Full-screen panel with small outer margin so the cyan border is visible
    PANEL_X = 40
    PANEL_Y = 40
    PANEL_W = 1840
    PANEL_H = 1000

    # Service row sizing (on 1920x1080 canvas)
    ROW_HEIGHT = 120
    ROW_START_Y = 120          # distance from top of panel to first row
    ROW_SPACING = 135          # vertical distance between rows

    def __init__(self, vault=None, account_info=None):
        super(AccountCardsWindow, self).__init__()
        self.vault = vault or {}
        self.account_info = account_info or {}
        self.controls = []
        self._build_ui()

    def _build_ui(self):
        """Build the window UI programmatically."""
        screen_width = self.getWidth()
        screen_height = self.getHeight()
        scale_x = screen_width / 1920.0
        scale_y = screen_height / 1080.0

        def sx(x): return int(x * scale_x)
        def sy(y): return int(y * scale_y)

        # ------------------------------------------
        # Full-screen solid dark background
        # ------------------------------------------
        bg_overlay = xbmcgui.ControlImage(
            0, 0, screen_width, screen_height,
            WHITE_TEX, colorDiffuse='FF0a1929'
        )
        self.addControl(bg_overlay)
        self.controls.append(bg_overlay)

        # Second layer for extra coverage (guarantees opacity)
        bg_overlay2 = xbmcgui.ControlImage(
            0, 0, screen_width, screen_height,
            WHITE_TEX, colorDiffuse='FF0a1929'
        )
        self.addControl(bg_overlay2)
        self.controls.append(bg_overlay2)

        # ------------------------------------------
        # Outer cyan border (glow frame)
        # ------------------------------------------
        border = xbmcgui.ControlImage(
            sx(self.PANEL_X - 4), sy(self.PANEL_Y - 4),
            sx(self.PANEL_W + 8), sy(self.PANEL_H + 8),
            WHITE_TEX,
            colorDiffuse=COLOR_BORDER[2:]
        )
        self.addControl(border)
        self.controls.append(border)

        # ------------------------------------------
        # Main panel background (solid dark blue)
        # ------------------------------------------
        panel_bg = xbmcgui.ControlImage(
            sx(self.PANEL_X), sy(self.PANEL_Y),
            sx(self.PANEL_W), sy(self.PANEL_H),
            WHITE_TEX,
            colorDiffuse='FF0d2137'
        )
        self.addControl(panel_bg)
        self.controls.append(panel_bg)

        # ------------------------------------------
        # Header: "Account Cards" title
        # ------------------------------------------
        header = xbmcgui.ControlLabel(
            sx(self.PANEL_X + 40), sy(self.PANEL_Y + 30),
            sx(900), sy(70),
            'Account Cards',
            font='font45',
            textColor=COLOR_TEXT_TITLE[2:]
        )
        self.addControl(header)
        self.controls.append(header)

        # Separator line under header (spans the left column only)
        sep_line = xbmcgui.ControlImage(
            sx(self.PANEL_X + 30), sy(self.PANEL_Y + 105),
            sx(1100), sy(3),
            WHITE_TEX,
            colorDiffuse=COLOR_BORDER[2:]
        )
        self.addControl(sep_line)
        self.controls.append(sep_line)

        # ------------------------------------------
        # Service rows (left column)
        # ------------------------------------------
        services = [
            ('REAL-DEBRID', 'rd_token', 'rd', 'rd.png'),
            ('PREMIUMIZE', 'pm_token', 'pm', 'pm.png'),
            ('ALLDEBRID', 'ad_token', 'ad', 'ad.png'),
            ('TRAKT', 'trakt_token', 'trakt', 'trakt.png'),
            ('TORBOX', 'tb_token', 'tb', 'tb.png'),
            ('TMDB', 'tmdb_api_key', 'tmdb', 'tmdb.png'),
        ]

        row_y = self.PANEL_Y + self.ROW_START_Y
        for i, (name, vault_key, info_key, icon_file) in enumerate(services):
            self._add_service_row(
                sx, sy,
                row_y + (i * self.ROW_SPACING),
                name, vault_key, info_key, icon_file
            )

            # Thin separator line under each row (except the last)
            if i < len(services) - 1:
                sep = xbmcgui.ControlImage(
                    sx(self.PANEL_X + 30), sy(row_y + (i * self.ROW_SPACING) + self.ROW_HEIGHT + 5),
                    sx(1100), sy(1),
                    WHITE_TEX,
                    colorDiffuse='6600d4ff'
                )
                self.addControl(sep)
                self.controls.append(sep)

        # ------------------------------------------
        # Right side: large addon icon & name
        # ------------------------------------------
        icon_size = 500
        icon_x = self.PANEL_X + self.PANEL_W - icon_size - 80
        icon_y = self.PANEL_Y + 180

        addon_icon = xbmcgui.ControlImage(
            sx(icon_x), sy(icon_y),
            sx(icon_size), sy(icon_size),
            ADDON_ICON
        )
        self.addControl(addon_icon)
        self.controls.append(addon_icon)

        # Addon name below icon
        addon_label = xbmcgui.ControlLabel(
            sx(icon_x), sy(icon_y + icon_size + 30),
            sx(icon_size), sy(50),
            ADDON_NAME,
            font='font30',
            textColor=COLOR_TEXT_WHITE[2:],
            alignment=0x00000002  # XBFONT_CENTER_X
        )
        self.addControl(addon_label)
        self.controls.append(addon_label)

        # ------------------------------------------
        # Close button (centered at the bottom of the panel)
        # ------------------------------------------
        btn_w = 320
        btn_h = 64
        btn_x = self.PANEL_X + (self.PANEL_W - btn_w) // 2
        btn_y = self.PANEL_Y + self.PANEL_H - btn_h - 30

        btn_bg = xbmcgui.ControlImage(
            sx(btn_x), sy(btn_y),
            sx(btn_w), sy(btn_h),
            WHITE_TEX,
            colorDiffuse='FF00d4ff'
        )
        self.addControl(btn_bg)
        self.controls.append(btn_bg)

        btn_label = xbmcgui.ControlLabel(
            sx(btn_x), sy(btn_y + 15),
            sx(btn_w), sy(btn_h - 20),
            'Press Back to Close',
            font='font24_title',
            textColor='FF000000',
            alignment=0x00000002
        )
        self.addControl(btn_label)
        self.controls.append(btn_label)

    def _add_service_row(self, sx, sy, y_pos, name, vault_key, info_key, icon_file):
        """Add a service row with name, status, details and icon."""
        row_x = self.PANEL_X + 30
        row_w = 1100
        row_h = self.ROW_HEIGHT

        # Row background (solid, slightly lighter than panel)
        row_bg = xbmcgui.ControlImage(
            sx(row_x), sy(y_pos),
            sx(row_w), sy(row_h),
            WHITE_TEX,
            colorDiffuse=COLOR_ROW_BG[2:]
        )
        self.addControl(row_bg)
        self.controls.append(row_bg)

        # Service name (cyan) - top of row
        name_label = xbmcgui.ControlLabel(
            sx(row_x + 25), sy(y_pos + 6),
            sx(700), sy(38),
            name,
            font='font27',
            textColor=COLOR_TEXT_TITLE[2:]
        )
        self.addControl(name_label)
        self.controls.append(name_label)

        # Status + detail lines
        status_text, status_color, detail_text = self._get_status(vault_key, info_key)
        status_label = xbmcgui.ControlLabel(
            sx(row_x + 25), sy(y_pos + 48),
            sx(900), sy(32),
            status_text,
            font='font22',
            textColor=status_color[2:]
        )
        self.addControl(status_label)
        self.controls.append(status_label)

        if detail_text:
            detail_label = xbmcgui.ControlLabel(
                sx(row_x + 25), sy(y_pos + 82),
                sx(900), sy(32),
                detail_text,
                font='font13',
                textColor=COLOR_TEXT_WHITE[2:]
            )
            self.addControl(detail_label)
            self.controls.append(detail_label)

        # Service icon (right side of row)
        icon_path = os.path.join(MEDIA_PATH, icon_file)
        if not xbmcvfs.exists(icon_path):
            icon_path = ADDON_ICON

        icon_w = 110
        icon_h = 90
        service_icon = xbmcgui.ControlImage(
            sx(row_x + row_w - icon_w - 20), sy(y_pos + (row_h - icon_h) // 2),
            sx(icon_w), sy(icon_h),
            icon_path
        )
        self.addControl(service_icon)
        self.controls.append(service_icon)

    def _get_status(self, vault_key, info_key):
        """Get (status_text, color, detail_text) for a service."""
        if not self.vault.get(vault_key):
            return 'Not authorized', COLOR_TEXT_STATUS_ERR, ''

        info = self.account_info.get(info_key)
        if not info:
            return 'Authorized', COLOR_TEXT_STATUS_OK, ''

        if info_key in ['rd', 'pm', 'ad']:
            days_left = info.get('days_left', 0)
            status = info.get('status', 'Active')
            expiry = info.get('expiration', 'N/A')
            fidelity = info.get('fidelity', 0)

            if days_left > 0:
                head = f'{status} - {days_left} days left (expires {expiry})'
            elif expiry and expiry != 'N/A':
                head = f'{status} - expired {expiry}'
            else:
                head = status

            # Detail line: identity + fidelity/space
            parts = []
            uname = info.get('username') or info.get('customer_id')
            if uname:
                parts.append(f'User: {uname}')
            if info_key == 'pm':
                space = info.get('space_used')
                if space:
                    parts.append(f'Storage: {space}')
            else:
                # RD and AD expose a fidelity/loyalty-points counter
                if fidelity:
                    parts.append(f'Fidelity: {fidelity:,} pts')
            detail = '   |   '.join(parts)
            return head, COLOR_TEXT_STATUS_OK, detail

        elif info_key == 'trakt':
            username = info.get('username', 'Unknown')
            vip_status = info.get('vip', 'Standard')
            joined = info.get('joined', '')
            total_min = info.get('total_minutes', 0)
            top_genre = info.get('top_genre', '')

            # Format total watch time
            if total_min >= 1440:
                days_float = total_min / 1440.0
                watch_str = f'{days_float:.1f}d watched'
            elif total_min > 0:
                watch_str = f'{total_min // 60}h watched'
            else:
                watch_str = ''

            head_parts = [f'{vip_status} - {username}']
            if joined:
                head_parts.append(f'joined {joined}')
            if watch_str:
                head_parts.append(watch_str)
            if top_genre:
                head_parts.append(f'Top: {top_genre}')
            head = '   |   '.join(head_parts)

            mw = info.get('movies_watched', 0)
            sw = info.get('shows_watched', 0)
            ew = info.get('episodes_watched', 0)
            cm = info.get('collected_movies', 0)
            cs = info.get('collected_shows', 0)
            wm = info.get('watchlist_movies', 0)
            ws = info.get('watchlist_shows', 0)
            lc = info.get('lists_count', 0)

            detail = (f'Watched: {mw} movies / {sw} shows ({ew} eps)   '
                      f'|   Collected: {cm} mov, {cs} shows   '
                      f'|   Watchlist: {wm}+{ws}   |   Lists: {lc}')
            return head, COLOR_TEXT_STATUS_OK, detail

        elif info_key == 'tb':
            return 'Authorized', COLOR_TEXT_STATUS_OK, ''

        elif info_key == 'tmdb':
            status = info.get('status', 'API Key Set')
            color = COLOR_TEXT_STATUS_OK if info.get('valid', True) else COLOR_TEXT_STATUS_ERR
            api_ver = info.get('api_version', '')
            tracked = info.get('tracked_changes', 0)
            parts = []
            if api_ver:
                parts.append(f'TMDB {api_ver}')
            if tracked:
                parts.append(f'{tracked:,} recent changes tracked')
            detail = '   |   '.join(parts)
            return status, color, detail

        return 'Authorized', COLOR_TEXT_STATUS_OK, ''

    def onAction(self, action):
        """Handle key/remote actions."""
        action_id = action.getId()
        if action_id in [xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK,
                         xbmcgui.ACTION_BACKSPACE, 92, 10, 7]:
            self.close()


def show_account_cards_window(vault, account_info=None):
    """
    Display the custom full-screen Account Cards window.

    Args:
        vault: Dictionary containing stored credentials
        account_info: Optional dict with detailed account info per service
                     Keys: 'rd', 'pm', 'ad', 'trakt', 'tb', 'tmdb'
    """
    if account_info is None:
        account_info = {}

    try:
        window = AccountCardsWindow(vault=vault, account_info=account_info)
        window.doModal()
        del window
    except Exception as e:
        xbmc.log(f'[The Accountant] Account Cards Window Error: {e}', xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Account Cards',
                            'Could not load custom window.\n'
                            f'Error: {str(e)}\n\n'
                            'Using fallback text viewer.')
        return False

    return True
