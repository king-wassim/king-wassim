import os
from datetime import datetime
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont

USERNAME = os.environ.get("USERNAME", "")
THEME = os.environ.get("THEME", "dark")
GH_TOKEN = os.environ.get("GH_TOKEN", "")

OUT_DIR = os.path.join("assets", "stats")
os.makedirs(OUT_DIR, exist_ok=True)

API_BASE = "https://api.github.com"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "king-wassim-readme-stats",
}
if GH_TOKEN:
    HEADERS["Authorization"] = "Bearer " + GH_TOKEN


def gh_get(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def format_num(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


def format_date(iso_text):
    if not iso_text:
        return "N/A"
    try:
        return datetime.fromisoformat(iso_text.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except Exception:
        return str(iso_text)


def load_font(size, bold=False):
    base = "/usr/share/fonts/truetype/dejavu"
    font_path = f"{base}/DejaVuSans-Bold.ttf" if bold else f"{base}/DejaVuSans.ttf"
    try:
        return ImageFont.truetype(font_path, size)
    except Exception:
        return ImageFont.load_default()


def theme_colors(theme):
    if theme == "dark":
        return {
            "bg": (13, 17, 23),
            "card": (22, 27, 34),
            "border": (48, 54, 61),
            "text": (230, 237, 243),
            "muted": (139, 148, 158),
            "accent": (88, 166, 255),
            "good": (63, 185, 80),
            "bar_bg": (36, 41, 47),
        }
    return {
        "bg": (255, 255, 255),
        "card": (245, 245, 245),
        "border": (210, 210, 210),
        "text": (24, 24, 24),
        "muted": (90, 90, 90),
        "accent": (9, 105, 218),
        "good": (26, 127, 55),
        "bar_bg": (226, 232, 240),
    }


def new_card(width, height, c):
    img = Image.new("RGB", (width, height), c["bg"])
    draw = ImageDraw.Draw(img)
    pad = 18
    draw.rounded_rectangle(
        (pad, pad, width - pad, height - pad),
        radius=22,
        fill=c["card"],
        outline=c["border"],
        width=2,
    )
    return img, draw


def draw_footer(draw, c, width, height):
    stamp = datetime.utcnow().strftime("Updated %Y-%m-%d %H:%M UTC")
    draw.text((36, height - 44), stamp, fill=c["muted"], font=load_font(16))
    draw.text((width - 250, height - 44), "source: GitHub API", fill=c["muted"], font=load_font(16))


def get_avatar(avatar_url):
    if not avatar_url:
        return None
    try:
        r = requests.get(avatar_url, timeout=30)
        r.raise_for_status()
        avatar = Image.open(BytesIO(r.content)).convert("RGB").resize((86, 86))
        mask = Image.new("L", avatar.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, 86, 86), fill=255)
        circular = Image.new("RGBA", avatar.size)
        circular.paste(avatar, (0, 0), mask)
        return circular
    except Exception:
        return None


def draw_stats_card(user, repos, stars, forks, out_path, theme="dark"):
    c = theme_colors(theme)
    width, height = 980, 430
    img, draw = new_card(width, height, c)

    name_font = load_font(34, bold=True)
    title_font = load_font(24, bold=True)
    body_font = load_font(22)
    value_font = load_font(22, bold=True)

    avatar = get_avatar(user.get("avatar_url"))
    if avatar:
        img.paste(avatar, (44, 48), avatar)
    draw.text((148, 52), f"{USERNAME} • GitHub Stats", fill=c["text"], font=name_font)
    draw.text((148, 96), user.get("name") or "", fill=c["muted"], font=body_font)

    left_lines = [
        ("Public repos", user.get("public_repos", 0)),
        ("Followers", user.get("followers", 0)),
        ("Following", user.get("following", 0)),
    ]
    right_lines = [
        ("Stars (public)", stars),
        ("Forks (public)", forks),
        ("Account created", format_date(user.get("created_at"))),
    ]

    draw.text((44, 165), "Overview", fill=c["text"], font=title_font)
    y = 210
    for label, value in left_lines:
        draw.text((44, y), label, fill=c["muted"], font=body_font)
        draw.text((300, y), format_num(int(value)), fill=c["accent"], font=value_font)
        y += 48

    y = 210
    for label, value in right_lines:
        draw.text((500, y), label, fill=c["muted"], font=body_font)
        txt = value if isinstance(value, str) else format_num(int(value))
        draw.text((760, y), txt, fill=c["good"], font=value_font)
        y += 48

    draw_footer(draw, c, width, height)
    img.save(out_path)


def draw_languages_card(top_langs, out_path, theme="dark"):
    c = theme_colors(theme)
    width, height = 980, 430
    img, draw = new_card(width, height, c)

    title_font = load_font(32, bold=True)
    body_font = load_font(22)
    value_font = load_font(20, bold=True)
    draw.text((44, 50), f"{USERNAME} • Top Languages", fill=c["text"], font=title_font)
    draw.text((44, 92), "Based on public repositories", fill=c["muted"], font=body_font)

    total = sum(v for _, v in top_langs) or 1
    bar_x, bar_w = 44, 700
    y = 150

    palette = [
        (88, 166, 255),
        (63, 185, 80),
        (210, 153, 34),
        (201, 209, 217),
        (248, 81, 73),
    ]
    for i, (lang, bytes_count) in enumerate(top_langs[:5]):
        pct = max(0.02, bytes_count / total)
        draw.text((bar_x, y), lang, fill=c["text"], font=body_font)
        draw.text((bar_x + bar_w + 28, y), f"{pct*100:5.1f}%", fill=c["accent"], font=value_font)

        top = y + 34
        draw.rounded_rectangle((bar_x, top, bar_x + bar_w, top + 20), radius=10, fill=c["bar_bg"])
        fill_w = int(bar_w * pct)
        draw.rounded_rectangle(
            (bar_x, top, bar_x + fill_w, top + 20),
            radius=10,
            fill=palette[i % len(palette)],
        )
        y += 56

    if not top_langs:
        draw.text((44, 170), "No language data available.", fill=c["muted"], font=body_font)

    draw_footer(draw, c, width, height)
    img.save(out_path)


def draw_activity_card(repos, out_path, theme="dark"):
    c = theme_colors(theme)
    width, height = 980, 310
    img, draw = new_card(width, height, c)

    title_font = load_font(30, bold=True)
    body_font = load_font(22)
    value_font = load_font(22, bold=True)
    draw.text((44, 48), f"{USERNAME} • Activity", fill=c["text"], font=title_font)

    pushed_dates = [r.get("pushed_at") for r in repos if r.get("pushed_at")]
    pushed_dates.sort(reverse=True)
    last_push = format_date(pushed_dates[0]) if pushed_dates else "N/A"
    archived = sum(1 for r in repos if r.get("archived"))
    repos_scanned = len(repos)

    lines = [
        ("Last push", last_push),
        ("Repositories scanned", format_num(repos_scanned)),
        ("Archived repositories", format_num(archived)),
    ]
    y = 112
    for label, value in lines:
        draw.text((44, y), label, fill=c["muted"], font=body_font)
        draw.text((360, y), str(value), fill=c["accent"], font=value_font)
        y += 52

    draw_footer(draw, c, width, height)
    img.save(out_path)


def main():
    if not USERNAME:
        raise SystemExit("USERNAME env var is required")

    try:
        user = gh_get(f"{API_BASE}/users/{USERNAME}")
    except requests.RequestException:
        user = {"login": USERNAME, "name": USERNAME, "public_repos": 0, "followers": 0, "following": 0}

    repos = []
    page = 1
    while True:
        try:
            data = gh_get(
                f"{API_BASE}/users/{USERNAME}/repos",
                params={"per_page": 100, "page": page, "type": "owner", "sort": "pushed"},
            )
        except requests.RequestException:
            break
        if not data:
            break
        repos.extend(data)
        page += 1
        if page > 10:
            break

    stars = sum(int(r.get("stargazers_count", 0)) for r in repos)
    forks = sum(int(r.get("forks_count", 0)) for r in repos)

    lang_totals = {}
    for r in repos[:30]:
        full = r.get("full_name")
        if not full:
            continue
        try:
            lang_data = gh_get(f"{API_BASE}/repos/{full}/languages")
        except requests.HTTPError:
            continue
        for lang, size in lang_data.items():
            lang_totals[lang] = lang_totals.get(lang, 0) + int(size)
    top_langs = sorted(lang_totals.items(), key=lambda kv: kv[1], reverse=True)[:5]

    draw_stats_card(user, repos, stars, forks, os.path.join(OUT_DIR, "stats.png"), theme=THEME)
    draw_languages_card(top_langs, os.path.join(OUT_DIR, "top-langs.png"), theme=THEME)
    draw_activity_card(repos, os.path.join(OUT_DIR, "activity.png"), theme=THEME)


if __name__ == "__main__":
    main()
  
