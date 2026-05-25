import random


def check_ticket_availability(attraction: str, date: str) -> str:
    """随机检查指定景点在某日期的门票状态。

    Args:
        attraction: 要查询的景点名称。
        date: 要查询的日期字符串。

    Returns:
        随机返回 `"available"` 或 `"sold_out"`，表示有票或售罄。

    Side Effects:
        不读写文件、不调用网络；仅使用本地随机数生成状态。
    """

    return random.choice(["available", "sold_out"])
