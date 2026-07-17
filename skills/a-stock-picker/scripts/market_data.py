# -*- coding: utf-8 -*-
"""市场数据客户端（多源，纯标准库，无第三方依赖）。

数据源选型（经实测稳定性，2026-07）：
- 新浪 vip.stock.finance.sina.com.cn：全市场 A 股列表 + 实时快照（价/PE/PB/涨跌幅/市值），稳定。
- 腾讯前复权日 K：主域 web.ifzq.gtimg.cn 自 2026-07-12 起持续 501 失效，改用镜像
  proxy.finance.qq.com/ifzqgtimg（同结构 data.<sym>.qfqday，连续请求稳定 ~70ms）。
- 东财 push2 / push2his 有 WAF 速率限制（连续请求被掐断 000），弃用。

接口：
- get_stock_list(): 全市场沪深 A 股列表 + 快照（code/name/price/pct/pe/pb/mktcap）
- get_klines(code, n=120): 个股近 n 日前复权日 K
- get_quote(codes): 批量实时行情（腾讯，GBK）
"""
import json
import time
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
# 主域 web.ifzq.gtimg.cn 自 2026-07-12 起持续返回 501 失效，改用同结构镜像。
TX_KLINE_URL = "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/fqkline/get"
TX_QUOTE_URL = "https://qt.gtimg.cn/q="
SINA_LIST_URL = ("http://vip.stock.finance.sina.com.cn/quotes_service/api/"
                 "json_v2.php/Market_Center.getHQNodeData")


def _fetch(url, retries=2, timeout=8, encoding="utf-8"):
    """GET 请求返回文本，失败重试。"""
    last = None
    for _ in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Referer": "https://finance.sina.com.cn/",
            })
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
            return raw.decode(encoding, errors="replace")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(0.3)
    raise RuntimeError(f"请求失败: {url[:80]} -> {last}")


def _fetch_json(url, **kw):
    return json.loads(_fetch(url, **kw))


def tx_symbol(code):
    """6 位股票代码 → 腾讯符号 sh/sz + code。"""
    code = str(code).zfill(6)
    # 沪市：60xxxx 主板、688xxx 科创板、900xxx B 股
    if code.startswith(("60", "68", "90")):
        return "sh" + code
    return "sz" + code  # 深市：000/001/002/300/301


def _parse_tx_kline_item(row):
    """腾讯 K线单行 [日期,开,收,高,低,量] → dict；非法返回 None。"""
    if not row or not isinstance(row, (list, tuple)) or len(row) < 6:
        return None
    try:
        return {
            "date": str(row[0]),
            "open": float(row[1]),
            "close": float(row[2]),
            "high": float(row[3]),
            "low": float(row[4]),
            "volume": float(row[5]),
        }
    except (ValueError, TypeError):
        return None


def get_klines(code, n=120):
    """腾讯前复权日 K，返回 list[dict]（旧→新），取最近 n 根。"""
    sym = tx_symbol(code)
    param = urllib.parse.quote("{0},day,,,{1},qfq".format(sym, n), safe=",")
    data = _fetch_json(TX_KLINE_URL + "?param=" + param)
    block = (data.get("data") or {}).get(sym) or {}
    series = block.get("qfqday") or block.get("day") or []
    parsed = [_parse_tx_kline_item(r) for r in series]
    cleaned = [k for k in parsed if k]
    return cleaned[-n:]


def _parse_sina_item(item):
    """新浪列表项 → 标准快照结构。亏损股 PE 为负值，保留交由策略层判断。"""
    def _num(k):
        v = item.get(k)
        if v in (None, ""):
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    return {
        "code": str(item.get("code", "") or ""),
        "name": str(item.get("name", "") or ""),
        "price": _num("trade"),
        "pct": _num("changepercent"),
        "pe": _num("per"),
        "pb": _num("pb"),
        "mktcap": _num("mktcap"),
    }


def get_stock_list(page_size=100, max_pages=80):
    """新浪全市场沪深 A 股列表 + 快照（仅主板/创业板/科创板，剔北交所/B股）。

    返回 list[dict]：{code,name,price,pct,pe,pb,mktcap}。ST/亏损由策略层过滤。
    """
    out = []
    for page in range(1, max_pages + 1):
        url = "%s?page=%d&num=%d&node=hs_a" % (SINA_LIST_URL, page, page_size)
        rows = _fetch_json(url)
        if not rows:
            break
        for r in rows:
            parsed = _parse_sina_item(r)
            code = parsed["code"]
            if not (code.startswith(("60", "00", "30", "68")) and code.isdigit()):
                continue  # 剔北交所(9/8/4 开头) 等
            out.append(parsed)
        if len(rows) < page_size:
            break
    return out


def get_quote(codes):
    """腾讯批量实时行情。codes 为代码列表，返回 dict[code] → {name,price,pre_close,open,volume}。

    腾讯返回 GBK 编码；字段以 ~ 分隔，索引：1=名称 2=代码 3=当前价 4=昨收 5=今开 6=成交量。
    """
    if isinstance(codes, str):
        codes = [codes]
    syms = ",".join(tx_symbol(c) for c in codes)
    text = _fetch(TX_QUOTE_URL + urllib.parse.quote(syms, safe=","), encoding="gbk")
    out = {}
    for c in codes:
        sym = tx_symbol(c)
        key = "v_" + sym + "=\""
        i = text.find(key)
        if i < 0:
            continue
        j = text.find("\"", i + len(key))
        if j < 0:
            continue
        parts = text[i + len(key):j].split("~")
        if len(parts) < 7:
            continue

        def _f(idx):
            try:
                return float(parts[idx])
            except (ValueError, IndexError):
                return None

        out[c] = {
            "name": parts[1],
            "price": _f(3),
            "pre_close": _f(4),
            "open": _f(5),
            "volume": _f(6),
        }
    return out
