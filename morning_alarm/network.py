import socket
import statistics
import time
from dataclasses import dataclass

import requests
from morning_alarm.defaults import (
    DEFAULT_DNS_TIMEOUT_SEC,
    DEFAULT_HTTP_TIMEOUT_SEC,
    DEFAULT_MAX_AVG_LATENCY_SEC,
    DEFAULT_NETWORK_CHECK_COUNT,
)


@dataclass(frozen=True)
class NetworkCheckConfig:
    """ネットワーク診断で使用する設定値。

    Attributes:
        dns_timeout_sec: DNS名前解決のタイムアウト秒。
        http_timeout_sec: HTTPリクエストのタイムアウト秒。
        check_count: HTTP疎通の試行回数。
        max_avg_latency_sec: 快適判定に使用する平均応答時間の上限秒。
    """

    dns_timeout_sec: float = DEFAULT_DNS_TIMEOUT_SEC
    http_timeout_sec: float = DEFAULT_HTTP_TIMEOUT_SEC
    check_count: int = DEFAULT_NETWORK_CHECK_COUNT
    max_avg_latency_sec: float = DEFAULT_MAX_AVG_LATENCY_SEC


DEFAULT_CONFIG = NetworkCheckConfig()


def diagnose_network(target_url: str, config: NetworkCheckConfig = DEFAULT_CONFIG) -> bool:
    """対象URLに対してネットワーク状態を診断する。

    DNS解決とHTTP疎通を計測し、成功率と平均応答時間から
    Selenium処理へ進めるかどうかを判定する。

    Args:
        target_url: 診断対象のURL。
        config: 診断のタイムアウト・回数・閾値の設定。

    Returns:
        bool:
            `True` は「快適に利用可能」判定。
            `False` は疎通失敗または応答遅延のため中止判定。
    """
    host = target_url.replace("https://", "").replace("http://", "").split("/")[0]

    print("ネットワーク診断を開始します...")
    socket.setdefaulttimeout(config.dns_timeout_sec)
    try:
        ip_address = socket.gethostbyname(host)
        print(f"DNS解決: OK ({host} -> {ip_address})")
    except OSError as error:
        print(f"DNS解決: NG ({error})")
        return False

    latencies: list[float] = []
    for idx in range(1, config.check_count + 1):
        started = time.perf_counter()
        try:
            response = requests.get(target_url, timeout=config.http_timeout_sec)
            elapsed = time.perf_counter() - started
            response.raise_for_status()
            latencies.append(elapsed)
            print(f"HTTP疎通 {idx}/{config.check_count}: OK ({elapsed:.3f}秒)")
        except requests.RequestException as error:
            elapsed = time.perf_counter() - started
            print(f"HTTP疎通 {idx}/{config.check_count}: NG ({elapsed:.3f}秒, {error})")

    success_rate = len(latencies) / config.check_count
    if not latencies:
        print("診断結果: NG (HTTPS疎通に失敗)")
        return False

    avg_latency = statistics.mean(latencies)
    print(
        "診断結果: "
        f"成功率 {success_rate * 100:.0f}% / 平均応答 {avg_latency:.3f}秒"
    )

    is_comfortable = success_rate == 1.0 and avg_latency <= config.max_avg_latency_sec
    if is_comfortable:
        print("判定: 快適にネット利用可能です。Selenium処理へ移行します。")
    else:
        print("判定: ネットワーク状態が不安定です。Selenium処理を中止します。")
    return is_comfortable
