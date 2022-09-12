import srcomapi
import srcomapi.datatypes as dt
import srdcHelper

api = srcomapi.SpeedrunCom()
api.debug = 1

game = srdcHelper.getGame(api, "Portal")
print(srdcHelper.getVariables(game))
