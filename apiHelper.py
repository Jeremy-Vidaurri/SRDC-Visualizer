import requests
from sqlHelper import sqlHelper
import heapq


class srcomAPI(object):
    def __init__(self):
        self.root = "https://www.speedrun.com/api"
        self.version = "v1"
        self.db = sqlHelper()
        connection = self.db.createCon("src.db")

        if not connection:
            raise Exception("Unable to access db")
        self.db.cur = self.db.con.cursor()

    def retrieveGameID(self, gameName: str) -> str:
        sql = "SELECT gameID FROM GAMES WHERE gameName = ?"
        sqlResponse = self.db.cur.execute(sql, [gameName])
        sqlResponse = sqlResponse.fetchone()

        # Game name is not cached yet
        if sqlResponse is None:
            PARAMS = {"name": gameName}
            url = self.root + '/' + self.version + '/games'

            request = requests.get(url, PARAMS)

            data = request.json()
            gameID = data['data'][0]['id']

            self.db.cacheGame(gameID, gameName)
        else:
            gameID = sqlResponse[0]

        return gameID

    def retrievePlayerColor(self, playerID: str) -> str:
        sql = "SELECT color FROM PLAYERS where playerID=?"
        sqlResponse = self.db.cur.execute(sql, [playerID])
        sqlResponse = sqlResponse.fetchone()

        if sqlResponse is None:
            url = self.root + '/' + self.version + '/users/' + playerID
            request = requests.get(url, None)

            data = request.json()

            if data['data']['name-style']['style'] == 'solid':
                color = data['data']['name-style']['color']['light']
            else:
                color = data['data']['name-style']['color-from']['light']

        else:
            color = sqlResponse[0]

        return color

    def retrievePlayerName(self, playerID: str) -> str:
        sql = "SELECT playerName FROM PLAYERS where playerID=?"
        sqlResponse = self.db.cur.execute(sql, [playerID])
        sqlResponse = sqlResponse.fetchone()

        if sqlResponse is None:
            url = self.root + '/' + self.version + '/users/' + playerID
            request = requests.get(url, None)

            data = request.json()
            playerName = data['data']['names']['international']
            color = self.retrievePlayerColor(playerID)

            self.db.cachePlayer(playerID, playerName, color)
        else:
            playerName = sqlResponse[0]

        return playerName

    def retrieveRuns(self, gameID: str, categoryID: str) -> None:
        if gameID == self.db.game and categoryID == self.db.category:
            print("Game is currently loaded")
            return

        # If we're loading eiter a new game or category, remove the old runs
        self.db.cur.execute("DELETE FROM RUNS")

        # Used to track the current loaded game
        self.db.game = gameID
        self.db.category = categoryID

        # https://www.speedrun.com/api/v1/runs?game=4pd0n31e&Category=lvdowokp&status=verified&orderby=date&direction=asc&max=200
        maxCount = 200
        url = self.root + '/' + self.version + '/runs'

        PARAMS = {"game": gameID, "category": categoryID, "status": "verified",
                  "orderby": "date", "direction": "asc", "max": maxCount}

        # HACK: store seen runs in a set so you don't double process them. Not sure if this has downsides yet.
        seenRuns = set()

        topTen = []
        heapq.heapify(topTen)
        offset = 0
        finished = False
        while not finished:
            request = requests.get(url, PARAMS)
            data = request.json()

            # Check if we are on the last page
            if offset == 9800:
                raise Exception("Too many runs to calculate")
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
                if not (run['date'] is not None and run['id'] not in seenRuns
                        and (len(topTen) < 10 or run['times']['primary_t'] < topTen[0][0] * -1)):
                    continue

                runID = run['id']

                # Guests do not have an ID/Account
                if run['players'][0]['rel'] != 'guest':
                    playerID = run['players'][0]['id']
                    color = self.retrievePlayerColor(playerID)
                    self.db.cachePlayer(
                        playerID, self.retrievePlayerName(playerID), color)
                else:
                    playerID = run['players'][0]['name']

                    self.db.cachePlayer(playerID, playerID, "#6699CC")

                # Date is stored in YYYY-MM-DD
                runDate = run['date']
                runTime = run['times']['primary_t']

                # Check to see if the runner is already top ten and remove their old time.
                for i, (time, player) in enumerate(topTen):
                    if player == playerID:
                        topTen.pop(i)

                if len(topTen) < 10:
                    heapq.heappush(topTen, (-runTime, playerID))
                else:
                    heapq.heappushpop(topTen, (-runTime, playerID))

                seenRuns.add(runID)
                playerName = self.retrievePlayerName(playerID)
                self.db.insertRun(runID, playerName, runDate, runTime)

    def retrieveCategories(self, gameID: str) -> list:
        sql = "SELECT categoryID, categoryName FROM CATEGORIES WHERE gameID=?"
        sqlResponse = self.db.cur.execute(sql, [gameID])
        sqlResponse = sqlResponse.fetchall()

        # Game categories is not cached yet
        if len(sqlResponse) == 0:
            url = self.root + '/' + self.version + '/games/' + gameID + '/categories'
            PARAMS = {"miscellaneous": False}
            request = requests.get(url, PARAMS)

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

    '''def retrieveRelease(self,gameID: str) -> str:
        url = self.root + '/' + self.version + '/games/' + gameID
        request = requests.get(url,[]) 

        data = request.json()
        return data['data']['release-date']'''
