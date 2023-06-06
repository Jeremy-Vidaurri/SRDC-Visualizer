import datetime
import time
import requests
from sqlHelper import sqlHelper


def compareDates(date1: str, date2: str):
    dt1 = datetime.datetime.fromisoformat(date1)
    dt2 = datetime.datetime.fromisoformat(date2)

    if dt1 == dt2:
        return 0
    elif dt1 > dt2:
        return 2
    else:
        return 1


class srcomAPI(object):
    def __init__(self):
        self.root = "https://www.speedrun.com/api"
        self.version = "v1"
        self.db = sqlHelper()
        connection = self.db.createCon("src.db")
        self.reqCount = 0

        if not connection:
            raise Exception("Unable to access db")
        self.db.cur = self.db.con.cursor()

    def retrieveGameID(self, gameName: str) -> str:
        sql = "SELECT gameID FROM GAMES WHERE gameName = ?"
        sqlResponse = self.db.cur.execute(sql, [gameName])
        sqlResponse = sqlResponse.fetchone()

        # Game name is not cached yet
        if sqlResponse is None:
            self.checkReqCount()
            PARAMS = {"name": gameName}
            url = self.root + '/' + self.version + '/games'

            request = requests.get(url, PARAMS)
            self.reqCount += 1

            data = request.json()
            gameID = data['data'][0]['id']

            self.db.cacheGame(gameID, gameName)
        else:
            gameID = sqlResponse[0]

        return gameID

    def retrievePlayerColor(self, playerID, data) -> str:
        sql = "SELECT color FROM PLAYERS where playerID=?"
        sqlResponse = self.db.cur.execute(sql, [playerID])
        sqlResponse = sqlResponse.fetchone()

        if sqlResponse is None:
            if data['data'][0]['name-style']['style'] == 'solid':
                color = data['data'][0]['name-style']['color']['light']
            else:
                color = data['data'][0]['name-style']['color-from']['light']
        else:
            color = sqlResponse[0]

        return color

    def retrievePlayerName(self, playerID: str, data) -> str:
        sql = "SELECT playerName FROM PLAYERS where playerID=?"
        sqlResponse = self.db.cur.execute(sql, [playerID])
        sqlResponse = sqlResponse.fetchone()

        if sqlResponse is None:
            playerName = data['data'][0]['names']['international']
            color = self.retrievePlayerColor(playerID, data)

            self.db.cachePlayer(playerID, playerName, color)
        else:
            playerName = sqlResponse[0]

        return playerName

    # TODO:
    #   * Add GUI to allow user to select game/category
    #   * In the GUI, add loading bar as information is collected.
    def retrieveRuns(self, gameID: str, categoryID: str) -> None:
        if gameID == self.db.game and categoryID == self.db.category:
            print("Game is currently loaded")
            return

        # If we're loading eiter a new game or category, remove the old runs
        self.db.cur.execute("DELETE FROM RUNS")

        # Used to track the current loaded game
        self.db.game = gameID
        self.db.category = categoryID

        # https://www.speedrun.com/api/v1/runs?game=4pdd0n31e&Category=lvdowokp&status=verified&orderby=date&direction=asc&max=200
        maxCount = 200
        url = self.root + '/' + self.version + '/runs'

        PARAMS = {"game": gameID, "category": categoryID, "status": "verified",
                  "orderby": "date", "direction": "asc", "max": maxCount, "embed": "players"}

        # HACK: store seen runs in a set, so you don't double process them. Not sure if this has downsides yet.
        seenRuns = set()

        lastDate = ""
        finished = False
        while not finished:
            self.checkReqCount()
            request = requests.get(url, PARAMS)
            self.reqCount += 1
            data = request.json()

            itemsReturned = data['pagination']['size']
            if itemsReturned != maxCount:
                finished = True
            else:
                # Information for the next page
                offset = data['pagination']['offset']
                PARAMS['offset'] = offset + itemsReturned

            # If there is no date, we can't add it into the visualizer
            # If the id has been seen, skip it
            # If the run isn't top ten, skip it
            for run in data['data']:
                runID = run['id']

                # Date is stored in YYYY-MM-DD
                runDate = run['date']
                runTime = run['times']['primary_t']

                if PARAMS['direction'] == 'desc' and compareDates(runDate, lastDate) == 1:
                    finished = True

                if runID in seenRuns:
                    continue

                # Guests do not have an ID/Account
                if run['players']['data'][0]['rel'] != 'guest':
                    playerID = run['players']['data'][0]['id']
                    color = self.retrievePlayerColor(playerID, run['players'])
                    self.db.cachePlayer(playerID, self.retrievePlayerName(playerID, run['players']), color)
                else:
                    playerID = run['players']['data'][0]['name']

                    self.db.cachePlayer(playerID, playerID, "#6699CC")

                seenRuns.add(runID)
                playerName = self.retrievePlayerName(playerID, run['players'])
                self.db.insertRun(runID, playerName, runDate, runTime)

            # Amount of runs > 10,000
            if PARAMS['offset'] == 10000 and not finished:
                time.sleep(60)
                PARAMS['direction'] = 'desc'
                lastDate = runDate
                PARAMS['offset'] = 0

    def retrieveCategories(self, gameID: str) -> list:
        sql = "SELECT categoryID, categoryName FROM CATEGORIES WHERE gameID=?"
        sqlResponse = self.db.cur.execute(sql, [gameID])
        sqlResponse = sqlResponse.fetchall()

        # Game categories is not cached yet
        if len(sqlResponse) == 0:
            self.checkReqCount()
            url = self.root + '/' + self.version + '/games/' + gameID + '/categories'
            PARAMS = {"miscellaneous": False}
            request = requests.get(url, PARAMS)
            self.reqCount += 1

            data = request.json()
            result = data['data']
            categories = []

            for category in result:
                if category['type'] == 'per-game':
                    catName = category['name']
                    catID = category['id']
                    categories.append((catID, catName))
                    self.db.cacheCategory(catID, catName, gameID)
        else:
            categories = sqlResponse

        return categories

    def getFirstRunDate(self, gameID: str, categoryID: str) -> str:
        self.checkReqCount()
        url = self.root + '/' + self.version + '/runs'
        PARAMS = {"game": gameID, "category": categoryID, "status": "verified", "max": 1, "direction": "asc",
                  "orderby": "date"}

        request = requests.get(url, PARAMS)
        self.reqCount += 1

        data = request.json()
        return data['data'][0]['date']

    def checkReqCount(self):
        if self.reqCount % 100 == 0 and self.reqCount != 0:
            time.sleep(60)
