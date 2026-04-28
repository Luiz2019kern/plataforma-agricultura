import requests


API_KEY = "7953fa29a8286188e91347ca7974f4cf"


def get_weather(city):

    url = f"https://api.openweathermap.org/data/2.5/weather?q={city},BR&appid={API_KEY}&units=metric&lang=pt_br"

    response = requests.get(url)

    if response.status_code != 200:
        return None

    data = response.json()

    return {
        "cidade": data["name"],
        "temp": data["main"]["temp"],
        "umidade": data["main"]["humidity"],
        "descricao": data["weather"][0]["description"],
        "vento": data["wind"]["speed"],
        "lat": data["coord"]["lat"],
        "lon": data["coord"]["lon"]
    }