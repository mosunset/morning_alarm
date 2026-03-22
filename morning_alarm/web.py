import time
from sys import platform

from morning_alarm.defaults import (
    DEFAULT_CLICK_WAIT_SEC,
    DEFAULT_TAB_STEP_WAIT_SEC,
    DEFAULT_VOLUME_PERCENT,
    DEFAULT_WEB_WAIT_TIMEOUT_SEC,
)
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def set_master_volume(percent: int) -> bool:
    """Windowsのマスター音量を指定パーセントへ設定する。

    Args:
        percent: 0から100までの整数値。

    Returns:
        bool:
            設定成功時は `True`、失敗時は `False`。

    Notes:
        - Windows以外では処理を行わず `False` を返す。
        - `pycaw` が利用できない場合も `False` を返す。
    """
    if platform != "win32":
        print("音量設定はWindows環境のみ対応です。")
        return False

    try:
        from pycaw.pycaw import AudioUtilities
    except ImportError as error:
        print(f"音量設定モジュールの読み込みに失敗しました: {error}")
        return False

    try:
        endpoint_volume = AudioUtilities.GetSpeakers().EndpointVolume
        endpoint_volume.SetMasterVolumeLevelScalar(
            max(0.0, min(1.0, percent / 100.0)), None
        )
        return True
    except Exception as error:
        print(f"音量設定に失敗しました: {error}")
        return False


def wait_until_page_loaded(
    driver: webdriver.Chrome, timeout_sec: int = DEFAULT_WEB_WAIT_TIMEOUT_SEC
) -> None:
    """ページのロード完了を待機する。

    Args:
        driver: 使用中のWebDriver。
        timeout_sec: 待機タイムアウト秒。
    """
    WebDriverWait(driver, timeout_sec).until(
        lambda current: current.execute_script("return document.readyState") == "complete"
    )


def click_after_page_loaded(
    driver: webdriver.Chrome,
    xpath: str,
    timeout_sec: int = DEFAULT_WEB_WAIT_TIMEOUT_SEC,
    click_wait_sec: float = DEFAULT_CLICK_WAIT_SEC,
) -> bool:
    """ページ読込完了後にXPath要素をクリックする。

    通常クリックに失敗した場合は、JavaScriptクリックへフォールバックする。

    Args:
        driver: 使用中のWebDriver。
        xpath: クリック対象のXPath。
        timeout_sec: 要素待機タイムアウト秒。
        click_wait_sec: ページ読込後にクリック前に待機する秒数。

    Returns:
        bool:
            クリック成功時は `True`、失敗時は `False`。
    """
    wait_until_page_loaded(driver, timeout_sec=timeout_sec)
    if click_wait_sec > 0:
        time.sleep(click_wait_sec)
    try:
        element = WebDriverWait(driver, timeout_sec).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        element.click()
        return True
    except (TimeoutException, WebDriverException):
        try:
            element = WebDriverWait(driver, timeout_sec).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            driver.execute_script("arguments[0].click();", element)
            return True
        except (TimeoutException, WebDriverException):
            return False


def open_and_focus_tab(
    driver: webdriver.Chrome,
    url: str,
    click_xpath: str | None = None,
    click_wait_sec: float = DEFAULT_CLICK_WAIT_SEC,
    timeout_sec: int = DEFAULT_WEB_WAIT_TIMEOUT_SEC,
) -> bool:
    """新しいタブでURLを開き、そのタブをアクティブにする。

    Args:
        driver: 使用中のWebDriver。
        url: 新規タブで開くURL。
        click_xpath: 指定された場合、タブを開いた後にクリックするXPath。
        click_wait_sec: クリック前に待機する秒数。
        timeout_sec: タブのロード完了待機タイムアウト秒。

    Returns:
        bool:
            新しいタブの作成と読み込みが成功した場合は `True`。
    """
    try:
        driver.switch_to.new_window("tab")
        driver.get(url)
        wait_until_page_loaded(driver, timeout_sec=timeout_sec)
        if click_xpath:
            clicked = click_after_page_loaded(
                driver,
                click_xpath,
                timeout_sec=timeout_sec,
                click_wait_sec=click_wait_sec,
            )
            if clicked:
                print(f"追加タブでクリック成功: {click_xpath}")
            else:
                print(f"追加タブでクリック失敗: {click_xpath}")
        return True
    except WebDriverException as error:
        print(f"追加入力タブのオープンに失敗しました: {error}")
        return False


def reload_tab_and_click(
    driver: webdriver.Chrome,
    tab_handle: str,
    click_xpath: str | None = None,
    click_wait_sec: float = DEFAULT_CLICK_WAIT_SEC,
    timeout_sec: int = DEFAULT_WEB_WAIT_TIMEOUT_SEC,
) -> bool:
    """指定タブをリロードし、必要ならクリックを実行する。

    Args:
        driver: 使用中のWebDriver。
        tab_handle: 操作対象タブのwindow handle。
        click_xpath: 指定された場合、リロード後にクリックするXPath。
        click_wait_sec: クリック前に待機する秒数。
        timeout_sec: リロード完了およびクリック待機タイムアウト秒。

    Returns:
        bool:
            リロード（および必要なクリック）が成功した場合は `True`。
    """
    try:
        driver.switch_to.window(tab_handle)
        driver.refresh()
        wait_until_page_loaded(driver, timeout_sec=timeout_sec)
        if click_xpath:
            return click_after_page_loaded(
                driver,
                click_xpath,
                timeout_sec=timeout_sec,
                click_wait_sec=click_wait_sec,
            )
        return True
    except WebDriverException as error:
        print(f"タブ更新に失敗しました: {error}")
        return False


def periodic_reload_and_reclick(
    driver: webdriver.Chrome,
    tab_targets: list[tuple[str, str | None, str]],
    interval_sec: int,
    click_wait_sec: float = DEFAULT_CLICK_WAIT_SEC,
    tab_step_wait_sec: float = DEFAULT_TAB_STEP_WAIT_SEC,
) -> None:
    """指定した複数タブを定期的にリロードし再クリックする。

    Args:
        driver: 使用中のWebDriver。
        tab_targets:
            `(tab_handle, click_xpath, label)` のリスト。
            `label` はログ出力用の識別名。
        interval_sec: リロード間隔（秒）。
        click_wait_sec: 各クリック前の待機秒数。
        tab_step_wait_sec: タブ切替ごとに追加で待機する秒数。
    """
    if interval_sec <= 0 or not tab_targets:
        return

    print(
        f"{interval_sec}秒ごとに{len(tab_targets)}タブをリロードし、"
        "必要なクリックを再実行します。"
    )
    cycle = 0
    while True:
        remaining = interval_sec
        while remaining > 0:
            print(f"\r次回リロードまで {remaining} 秒", end="", flush=True)
            time.sleep(1)
            remaining -= 1
        print()
        cycle += 1
        print(f"定期更新サイクル {cycle} を開始します。")
        for tab_handle, click_xpath, label in tab_targets:
            success = reload_tab_and_click(
                driver,
                tab_handle,
                click_xpath=click_xpath,
                click_wait_sec=click_wait_sec,
            )
            if success:
                print(f"{label}: リロードと再クリックに成功しました。")
            else:
                print(f"{label}: リロードまたは再クリックに失敗しました。")
            if tab_step_wait_sec > 0:
                time.sleep(tab_step_wait_sec)


def open_web_page(
    url: str,
    click_xpath: str | None = None,
    followup_tab_url: str | None = None,
    followup_tab_click_xpath: str | None = None,
    volume_percent: int = DEFAULT_VOLUME_PERCENT,
    click_wait_sec: float = DEFAULT_CLICK_WAIT_SEC,
    reload_interval_sec: int | None = None,
    tab_step_wait_sec: float = DEFAULT_TAB_STEP_WAIT_SEC,
    keep_browser_open: bool = True,
) -> None:
    """サイトを開き、必要な後続処理を実行する。

    Args:
        url: アクセスするURL。
        click_xpath:
            指定された場合はページ読込完了後にクリックを実行する。
            クリック成功時は10秒待機し、PC音量を40%へ設定する。
        followup_tab_url:
            指定された場合、最後に新しいタブでこのURLを開いて
            そのタブをアクティブにする。
        followup_tab_click_xpath:
            指定された場合、追加タブの読込後にこのXPathをクリックする。
        volume_percent:
            初回クリック後に設定するWindowsマスター音量（0-100）。
        click_wait_sec:
            ページ読込後、クリック実行前に待機する秒数。
        reload_interval_sec:
            指定された場合、処理完了後にこの秒数間隔で対象タブを
            リロードし、指定XPathを再クリックし続ける。
        tab_step_wait_sec:
            定期更新時、タブ処理ごとに挿入する待機秒数。
        keep_browser_open:
            `True` の場合は処理終了後もブラウザを開いたままにする。
    """
    options = Options()
    options.add_argument("--start-maximized")
    if keep_browser_open:
        options.add_experimental_option("detach", True)

    driver = webdriver.Chrome(options=options)
    should_quit = not keep_browser_open
    try:
        tab_targets: list[tuple[str, str | None, str]] = []
        driver.get(url)
        print(f"アクセス成功: {driver.title}")
        main_tab_handle = driver.current_window_handle
        if click_xpath:
            clicked = click_after_page_loaded(
                driver,
                click_xpath,
                click_wait_sec=click_wait_sec,
            )
            if clicked:
                print(f"クリック成功: {click_xpath}")
                if set_master_volume(volume_percent):
                    print(f"PC音量を{volume_percent}%に設定しました。")
                else:
                    print(f"PC音量を{volume_percent}%に設定できませんでした。")
            else:
                print(f"クリック失敗: {click_xpath}")
        tab_targets.append((main_tab_handle, click_xpath, "メインタブ"))
        if followup_tab_url:
            if open_and_focus_tab(
                driver,
                followup_tab_url,
                click_xpath=followup_tab_click_xpath,
                click_wait_sec=click_wait_sec,
            ):
                tab_targets.append(
                    (driver.current_window_handle, followup_tab_click_xpath, "追加タブ")
                )
                print(f"追加タブを開いてアクティブ化しました: {followup_tab_url}")
            else:
                print(f"追加タブを開けませんでした: {followup_tab_url}")
        if reload_interval_sec is not None:
            periodic_reload_and_reclick(
                driver,
                tab_targets=tab_targets,
                interval_sec=reload_interval_sec,
                click_wait_sec=click_wait_sec,
                tab_step_wait_sec=tab_step_wait_sec,
            )
    finally:
        if should_quit:
            driver.quit()
