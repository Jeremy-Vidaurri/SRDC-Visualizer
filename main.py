from sqlHelper import sqlHelper
from apiHelper import srcomAPI
from visualizer import Visualizer
import pandas as pd
from datetime import date


def sql_to_csv(db):
    db_df = pd.read_sql_query(
        "SELECT playerName,runDate,runTime FROM RUNS", db.con)
    db_df.to_csv('database.csv', index=False)


def colorDict(db) -> dict:
    sql = "SELECT playerName,color FROM PLAYERS"
    db.cur = db.con.cursor()
    sqlResponse = db.cur.execute(sql, [])
    sqlResponse = sqlResponse.fetchall()
    colors = {}
    for player, color in sqlResponse:
        if player not in colors:
            colors[player] = color

    return colors


def main():
    db = sqlHelper()
    connected = db.createCon("src.db")

    if not connected:
        raise Exception("Unable to connect to database.")

    db.initTables()

    api = srcomAPI()
    id = api.retrieveGameID("Dark Souls III")
    categories = api.retrieveCategories(id)
    api.retrieveRuns(id, categories[0][0])
    db.con.commit()

    sql_to_csv(db)

    sql = "SELECT min(runDate) FROM RUNS"
    db.cur = db.con.cursor()
    data = db.cur.execute(sql, [])
    startDate = data.fetchone()[0]

    vis = Visualizer(startDate, str(date.today()), colorDict(db))
    vis.display()


if __name__ == "__main__":
    main()
