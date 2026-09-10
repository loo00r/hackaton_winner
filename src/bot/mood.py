MOODS = (
    (("дурний", "тупий", "ідіот", "фігня", "бісить", "нахрін"), "Evil", "😈", "🌡️", 0.65),
    (("чорт", "блін", "не можу", "помилка", "не працює"), "Sad", "😔", "🧊", 0.25),
    (("лол", "хаха", "круто", "топ", "супер"), "Happy", "😎", "🔥", 0.85),
)


def mood_status(text: str) -> str:
    lowered = text.lower()
    for words, mood, emoji, temperature_emoji, temperature in MOODS:
        if any(word in lowered for word in words):
            return f"[🤖 Status: {mood} {emoji} | {temperature_emoji} Temp: {temperature:.2f}]"
    return "[🤖 Status: Neutral 🤖 | ❄️ Temp: 0.55]"
