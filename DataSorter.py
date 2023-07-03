import datetime
import heapq
import csv


class DataSorter(object):
    def __init__(self, path):
        self.path = path

    def topTenOnly(self):
        topTen = []
        heapq.heapify(topTen)

        output = open('topTen.csv', mode='w', newline='')
        output_writer = csv.writer(output)

        with open(self.path) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            line = 0
            for row in csv_reader:
                if line == 0:
                    line += 1
                    continue
                elif 0 < line < 11:
                    heapq.heappush(topTen, [-float(row[2]), row[0], row[1]])
                else:
                    heapq.heappushpop(topTen, [-float(row[2]), row[0], row[1]])
                line += 1
                latest = self.latestDate(topTen)

                # run[0] is time, 1 is user, 2 is date
                # Still not getting the correct data
                for run in topTen:
                    time = float(-run[0])
                    output_writer.writerow([latest, run[1], time])

        output.close()

    def latestDate(self, runs):
        dates = [datetime.datetime.fromisoformat(run[2]) for run in runs]
        return max(dates)
