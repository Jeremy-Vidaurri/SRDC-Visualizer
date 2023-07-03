import sqlite3
from sqlite3 import Error


class sqlHelper(object):

    def __init__(self):
        self.con = None
        self.cur = None
        self.game = None
        self.category = None

    # Connect to the local database and return if the connection was successful
    def createCon(self, path: str) -> bool:
        try:
            connection = sqlite3.connect(path)
        except Error as e:
            raise Exception(f"Error:{e}")

        self.con = connection
        if self.con:
            self.cur = self.con.cursor()

        return self.con is not None

    # Creates the necessary tables on startup given that they don't exist
    def initTables(self) -> None:

        games = "CREATE TABLE IF NOT EXISTS GAMES( \
            gameName TEXT NOT NULL,\
            gameID TEXT NOT NULL, \
            PRIMARY KEY(gameName))"
        players = "CREATE TABLE IF NOT EXISTS PLAYERS( \
            playerName TEXT NOT NULL,\
            playerID TEXT NOT NULL, \
            color TEXT NOT NULL, \
            PRIMARY KEY(playerID))"
        runs = "CREATE TABLE IF NOT EXISTS RUNS( \
            runID TEXT NOT NULL,\
            playerName TEXT NOT NULL,\
            runDate TEXT NOT NULL, \
            runTime REAL,\
            PRIMARY KEY(runID,runDate))"
        categories = "CREATE TABLE IF NOT EXISTS CATEGORIES(\
            gameID TEXT NOT NULL, \
            categoryID TEXT NOT NULL, \
            categoryName TEXT NOT NULL,\
            PRIMARY KEY(categoryID))"

        for v in [games, players, runs, categories]:
            self.cur.execute(v)
            self.con.commit()

    # Adds a game to the game table so that we don't have to do a GET request
    #   every time we wish to access the game's runs
    def cacheGame(self, gameID: str, gameName: str) -> None:
        checkSQL = "SELECT * FROM GAMES where gameID=?"
        response = self.cur.execute(checkSQL, [gameID])

        response = response.fetchone()
        if response is not None:
            return

        sql = "INSERT INTO GAMES (gameName, gameID)\
            VALUES(?,?)"

        self.cur.execute(sql, [gameName, gameID])
        self.con.commit()

    # Adds a player to the players table so that we don't have to do a GET request
    #   every time we wish to access a player's name
    def cachePlayer(self, playerID: str, playerName: str, color: str) -> None:

        checkSQL = "SELECT * FROM PLAYERS where playerID=?"
        response = self.cur.execute(checkSQL, [playerID])

        response = response.fetchone()
        if response is not None:
            return

        insertionSQL = "INSERT INTO PLAYERS (playerName, playerID, color)\
            VALUES(?,?,?)"

        self.cur.execute(insertionSQL, [playerName, playerID, color])
        self.con.commit()

    def cacheCategory(self, categoryID, categoryName, gameID):
        checkSQL = "SELECT * FROM CATEGORIES WHERE categoryID = ?"
        response = self.cur.execute(checkSQL, [categoryID])
        response = response.fetchone()

        if response is not None:
            return

        insertionSQL = "INSERT INTO CATEGORIES(gameID, categoryID, categoryName)\
            VALUES (?, ?, ?)"
        self.cur.execute(insertionSQL, [gameID, categoryID, categoryName])
        self.con.commit()

    # Adds a run to the runs table
    # Used to get the top ten times based on date

    def insertRun(self, runID: str, playerName: str, runDate: str, runTime: float):
        sql = "INSERT INTO RUNS (runID, playerName, runDate, runTime)\
            VALUES (?, ?, ?, ?)"
        self.cur.execute(sql, [runID, playerName, runDate, runTime])
        self.con.commit()
