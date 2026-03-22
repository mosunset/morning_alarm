import argparse

from morning_alarm.defaults import (
    DEFAULT_CLICK_WAIT_SEC,
    DEFAULT_RELOAD_INTERVAL_MINUTES,
    DEFAULT_TAB_STEP_WAIT_SEC,
    DEFAULT_VOLUME_PERCENT,
)
from morning_alarm.network import diagnose_network
from morning_alarm.web import open_web_page

SITES: dict[str, str] = {
    "web117": "https://web117.jp/",
    "azo234": "https://azo234.github.io/timesignal/",
    "piliapp": "https://jp.piliapp.com/time-now/jp/117/",
}

CLICK_XPATHS: dict[str, str] = {
    "web117": "/html/body/section/div[1]/p[2]/button",
    "azo234": "/html/body",
    "piliapp": "/html/body/div[2]/div/div[1]/div/div[3]/div[1]/div/div[1]/div[1]/i",
}

SITE_ALIASES: dict[str, str] = {
    "1": "web117",
    "2": "azo234",
    "3": "piliapp",
}

DEFAULT_SITE_KEY = "web117"
FOLLOWUP_TAB_URL = "https://www.nict.go.jp/JST/JST6/index.html"
FOLLOWUP_TAB_CLICK_XPATH = "/html/body/footer/nav/div[2]/div/input"


def parse_site(value: str) -> str:
    """サイト指定値を正規化してサイトキーへ変換する。"""
    site_key = SITE_ALIASES.get(value.strip().lower(), value.strip().lower())
    if site_key not in SITES:
        raise argparse.ArgumentTypeError(
            "site は 1,2,3 または web117, azo234, piliapp を指定してください。"
        )
    return site_key


def parse_volume_percent(value: str) -> int:
    """音量引数を0-100の整数として検証する。"""
    try:
        percent = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("volume_percent は整数で指定してください。") from error

    if percent < 0 or percent > 100:
        raise argparse.ArgumentTypeError("volume_percent は 0-100 の範囲で指定してください。")
    return percent


def parse_reload_minutes(value: str) -> int:
    """更新間隔引数を1以上の整数として検証する。"""
    try:
        minutes = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("reload_minutes は整数で指定してください。") from error

    if minutes < 1:
        raise argparse.ArgumentTypeError("reload_minutes は 1 以上で指定してください。")
    return minutes


def parse_args() -> argparse.Namespace:
    """CLI引数を解析して実行設定を返す。"""
    parser = argparse.ArgumentParser(
        description="時報サイト自動操作（クリック・音量設定・定期リロード）"
    )
    parser.add_argument(
        "-s",
        "--site",
        default=DEFAULT_SITE_KEY,
        type=parse_site,
        help="対象サイト: 1/2/3 または web117/azo234/piliapp（既定: web117）",
    )
    parser.add_argument(
        "-v",
        "--volume",
        dest="volume_percent",
        default=DEFAULT_VOLUME_PERCENT,
        type=parse_volume_percent,
        help=f"Windows音量 (0-100, 既定: {DEFAULT_VOLUME_PERCENT})",
    )
    parser.add_argument(
        "-r",
        "--reload-minutes",
        dest="reload_minutes",
        default=DEFAULT_RELOAD_INTERVAL_MINUTES,
        type=parse_reload_minutes,
        help=f"定期更新間隔（分, 既定: {DEFAULT_RELOAD_INTERVAL_MINUTES}）",
    )
    return parser.parse_args()


def main() -> None:
    """アプリ本体の実行フローを制御する。

    処理手順:
    1. 対象サイトを解決
    2. ネットワーク診断を実施
    3. サイトごとのクリック対象XPathを選択
    4. Seleniumでサイトを開いてクリック処理へ進む
    5. 指定分ごとに2タブをリロードして再クリック
    """
    args = parse_args()
    site_key = args.site
    target_url = SITES[site_key]
    volume_percent = args.volume_percent
    reload_interval_minutes = args.reload_minutes
    print(f"選択サイト: {site_key} ({target_url})")
    print(
        f"実行設定: 音量 {volume_percent}% / "
        f"定期更新 {reload_interval_minutes}分ごと / "
        f"クリック前待機 {DEFAULT_CLICK_WAIT_SEC}秒 / "
        f"タブ間待機 {DEFAULT_TAB_STEP_WAIT_SEC}秒"
    )
    if not diagnose_network(target_url):
        return

    click_xpath = CLICK_XPATHS.get(site_key)
    open_web_page(
        target_url,
        click_xpath=click_xpath,
        followup_tab_url=FOLLOWUP_TAB_URL,
        followup_tab_click_xpath=FOLLOWUP_TAB_CLICK_XPATH,
        volume_percent=volume_percent,
        click_wait_sec=DEFAULT_CLICK_WAIT_SEC,
        reload_interval_sec=reload_interval_minutes * 60,
        tab_step_wait_sec=DEFAULT_TAB_STEP_WAIT_SEC,
        keep_browser_open=True,
    )


if __name__ == "__main__":
    main()
