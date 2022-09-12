import srcomapi
import srcomapi.datatypes as dt


def getGame(api, name: str):
    des = api.search(dt.Game, {"name": name})
    return des[0]


def getVariables(game) -> set:
    categories = set()
    cats = [cat for cat in game.categories if cat.type == "per-game"]
    for cat in cats:
        for variable in cat.variables:
            if variable.data["is-subcategory"]:
                categories.add(variable.data["name"])
    return categories
