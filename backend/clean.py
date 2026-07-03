"""机械清洗:在 Vision 提取的 ocr_text 上做兜底剥离。

主力剥离已由 Vision prompt 完成(§6),这里规则从简,只清明显残留:
状态栏、纯 URL 行、明显 UI 词行、多余空行。不改写正文。
"""
import re

# 状态栏时间(9:41 / 09:41 / 23:07),整行就是它
_STATUS_TIME = re.compile(r"^\s*\d{1,2}:\d{2}\s*$")
# 纯 URL 行
_URL_LINE = re.compile(r"^\s*(https?://|www\.)\S+\s*$", re.I)
# 明显 UI 词(整行且很短时才删,避免误伤正文里出现这些字)
_UI_WORDS = {
    "点赞", "关注", "已关注", "回复", "评论", "转发", "分享", "收藏",
    "搜索", "更多", "查看更多", "展开全文", "赞", "举报", "私信", "复制",
    "下载", "立即下载", "打开App", "打开 App",
}
# 状态栏电量/信号残留碎词
_STATUS_JUNK = re.compile(r"^\s*(\d+%|[·•]+|5G|4G|LTE|Wi-?Fi)\s*$", re.I)


def clean_text(raw: str | None) -> str:
    """返回去噪后的正文。输入空则返回空串。"""
    if not raw:
        return ""

    kept: list[str] = []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            kept.append("")  # 暂留,稍后压缩连续空行
            continue
        if _STATUS_TIME.match(s):
            continue
        if _URL_LINE.match(s):
            continue
        if _STATUS_JUNK.match(s):
            continue
        # 整行由 UI 词构成(允许空格分隔,如 "点赞 评论 转发"),且 token 不多
        tokens = s.split()
        if 1 <= len(tokens) <= 5 and all(t in _UI_WORDS for t in tokens):
            continue
        kept.append(s)

    # 压缩连续空行为最多一个,去首尾空行
    out: list[str] = []
    for line in kept:
        if line == "" and (not out or out[-1] == ""):
            continue
        out.append(line)
    while out and out[-1] == "":
        out.pop()

    return "\n".join(out)
