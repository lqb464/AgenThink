import re

# Demo data — no real API call in this learning level.
CITY_WEATHER = {
    "hà nội": "Hà Nội: 28°C, trời nhiều mây",
    "ha noi": "Hà Nội: 28°C, trời nhiều mây",
    "hanoi": "Hà Nội: 28°C, trời nhiều mây",
    "đà nẵng": "Đà Nẵng: 31°C, nắng nhẹ",
    "da nang": "Đà Nẵng: 31°C, nắng nhẹ",
    "hồ chí minh": "Hồ Chí Minh: 33°C, nóng ẩm",
    "ho chi minh": "Hồ Chí Minh: 33°C, nóng ẩm",
    "sài gòn": "Hồ Chí Minh: 33°C, nóng ẩm",
    "sai gon": "Hồ Chí Minh: 33°C, nóng ẩm",
}


def weather(city: str) -> str:
    key = city.strip().lower()
    return CITY_WEATHER.get(key, f"Chưa có dữ liệu thời tiết cho '{city}'.")


def match_weather(message: str) -> str | None:
    text = message.strip()
    lowered = text.lower()

    is_weather_question = any(
        keyword in lowered
        for keyword in ("thời tiết", "nhiệt độ", "bao nhiêu độ")
    )
    if not is_weather_question:
        return None

    for city in CITY_WEATHER:
        if city in lowered:
            return weather(city)

    # Fallback: try text after "ở" / "tại"
    match = re.search(r"(?:ở|tại)\s+(.+)$", text, flags=re.IGNORECASE)
    if match:
        return weather(match.group(1).strip(" ?."))

    return None
