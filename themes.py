from textual.theme import Theme

SKINS = {
    "라이트": {
        "bg": "#f4f1eb", "panel": "#ebe7df", "fg": "#111111", "muted": "#4d4a45",
        "accent": "#2f6fed", "button": "#e4e0d8", "entry": "#fffdf8"
    },
    "다크": {
        "bg": "#171a1f", "panel": "#20242b", "fg": "#f4f4f5", "muted": "#b9c0cc",
        "accent": "#7aa2ff", "button": "#2d333d", "entry": "#111418"
    },
    "블루": {
        "bg": "#edf4ff", "panel": "#dfeaff", "fg": "#0d1b2a", "muted": "#43556f",
        "accent": "#1d4ed8", "button": "#d7e5ff", "entry": "#ffffff"
    },
    "웜": {
        "bg": "#fff4e8", "panel": "#f4dfc8", "fg": "#25170d", "muted": "#6a4b31",
        "accent": "#c05621", "button": "#efd1ad", "entry": "#fffaf3"
    },
    "286 터미널": {
        "bg": "#050805", "panel": "#071407", "fg": "#39ff14", "muted": "#18a318",
        "accent": "#00ff66", "button": "#0b240b", "entry": "#000000"
    },
    "NASA 콘솔": {
        "bg": "#06121f", "panel": "#0b1d33", "fg": "#d7e9ff", "muted": "#78a6c8",
        "accent": "#ffb000", "button": "#102b49", "entry": "#020912"
    },
    "월스트리트": {
        "bg": "#060606", "panel": "#111111", "fg": "#ffb84d", "muted": "#8fa3a3",
        "accent": "#ff7a00", "button": "#1b1b1b", "entry": "#000000"
    },
    "CIA 블랙파일": {
        "bg": "#0b0d0a", "panel": "#151a12", "fg": "#e8e0c8", "muted": "#8f9779",
        "accent": "#b21f2d", "button": "#20261b", "entry": "#050605"
    },
    "항공모함 CIC": {
        "bg": "#061016", "panel": "#0b1c24", "fg": "#d7f7e8", "muted": "#6f9f9c",
        "accent": "#00d084", "button": "#102a35", "entry": "#02090d"
    },
    "핵시설 벙커": {
        "bg": "#0c0f08", "panel": "#191d11", "fg": "#e6f0b8", "muted": "#8a9364",
        "accent": "#d6ff00", "button": "#242815", "entry": "#050702"
    },
    "해치 108": {
        "bg": "#07100e", "panel": "#0f1d18", "fg": "#b7f7d0", "muted": "#6b8f7a",
        "accent": "#00e0a4", "button": "#16251f", "entry": "#020706"
    },
    "매트릭스": {
        "bg": "#000500", "panel": "#001100", "fg": "#9cff9c", "muted": "#2bd62b",
        "accent": "#00ff41", "button": "#001a00", "entry": "#000000"
    },
    "ENIAC 진공관": {
        "bg": "#1a1208", "panel": "#2a1b0d", "fg": "#ffd18a", "muted": "#9a7348",
        "accent": "#ff8c1a", "button": "#3a250f", "entry": "#0b0703"
    },
    "오더 컨트롤": {
        "bg": "#08050f", "panel": "#120b1f", "fg": "#f4e7c5", "muted": "#8f7aa8",
        "accent": "#d4af37", "button": "#1b112b", "entry": "#030207"
    }
}

def register_all_themes(app):
    for idx, (name, colors) in enumerate(SKINS.items()):
        is_dark = name not in ["라이트", "웜", "블루"]
        t = Theme(
            name=f"theme_{idx}",
            primary=colors["accent"],
            secondary=colors["button"],
            foreground=colors["fg"],
            background=colors["bg"],
            surface=colors["panel"],
            panel=colors["panel"],
            dark=is_dark
        )
        app.register_theme(t)
