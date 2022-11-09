import asyncio
import csv
import json
from dataclasses import dataclass, fields, astuple
from datetime import time
import time as tm
import httpx as httpx
from httpx import AsyncClient


response = httpx.get(
    "https://www.zooplus.de/tierarzt/api/v2/token?debug=authReduxMiddleware-tokenIsExpired"
).content
TOKEN = json.loads(response)["token"]


@dataclass
class Veterinarian:
    name: str
    subtitle: str
    address: str
    work_time: list
    count_reviews: int
    avg_review_score: int


VETERINARIAN_FIELDS = [field.name for field in fields(Veterinarian)]


def get_work_time(work_time: list) -> list:

    """Edits the working hours display"""

    days_week = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}

    for day in work_time:
        day["day"] = days_week[day["day"]]

        if len(str(day["from"])) == 3:
            hour = int(str(day["from"])[0])
            minutes = int(str(day["from"])[1:])
            day["from"] = time(hour, minutes).strftime("%H:%M")
        else:
            hour = int(str(day["from"])[:2])
            try:
                minutes = int(str(day["from"])[2:])
            except ValueError:
                pass
            day["from"] = time(hour, minutes).strftime("%H:%M")

        if len(str(day["to"])) == 3:
            hour = int(str(day["to"])[0])
            minutes = int(str(day["to"])[1:])
            day["to"] = time(hour, minutes).strftime("%H:%M")
        else:
            hour = int(str(day["to"])[:2])
            try:
                minutes = int(str(day["to"])[2:])
            except ValueError:
                pass
            day["to"] = time(hour, minutes).strftime("%H:%M")

    return work_time


def get_one_veterinarian(inf: dict) -> Veterinarian:

    """Gets one object Veterinarian"""

    return Veterinarian(
        name=inf["name"],
        subtitle=inf.get("subtitle"),
        address=f"{inf.get('address')}, {inf.get('zip')} {inf['city']}",
        work_time=get_work_time(inf["open_time"]),
        count_reviews=inf["count_reviews"],
        avg_review_score=inf.get("avg_review_score"),
    )


async def get_veterinarians_page(num_page: int, client: AsyncClient) -> [Veterinarian]:

    """Gets all veterinarians from one page"""

    if num_page == 1:
        url = "https://www.zooplus.de/tierarzt/api/v2/results?animal_99=true&page=1&from=0&size=20"
    else:
        url = f"https://www.zooplus.de/tierarzt/api/v2/results?animal_99=true&page={num_page}&from={num_page}0&size=20"

    page = await client.get(url, headers={"authorization": f"Bearer {TOKEN}"})
    information = json.loads(page.content)

    return [get_one_veterinarian(inf) for inf in information["results"]]


async def get_all_veterinarians(client: AsyncClient) -> [Veterinarian]:

    """Gets all veterinarians from five pages"""

    all_veterinarians = []

    veterinarians_page = await asyncio.gather(
        *[get_veterinarians_page(num_page, client) for num_page in range(1, 6)]
    )

    for veterinarian in veterinarians_page:
        all_veterinarians.extend(veterinarian)

    return all_veterinarians


async def write_products_to_csv():

    """Writes received information about all veterinarians to a csv file """

    with open("veterinarians.csv", "w", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(VETERINARIAN_FIELDS)

        async with AsyncClient() as client:
            writer.writerows(
                astuple(veterinarian)
                for veterinarian in await get_all_veterinarians(client)
            )


if __name__ == "__main__":
    start_time = tm.perf_counter()

    asyncio.run(write_products_to_csv())

    end_time = tm.perf_counter()
    print("Elapsed:", round(end_time - start_time, 6))
