"""Repackages sea ice parcel trajectories"""

from pathlib import Path

import csv
import datetime as dt

import numpy as np
import xarray as xr

from affine import Affine


GEOTRANSFORM = (-4524683.8, 25067.5, 0.0, 4524683.8, 0.0, 25067.5)
PROJECTION = "+proj=laea +lat_0=90 +lon_0=0 +x_0=0 +y_0=0 +a=6371228 +b=6371228 +units=m +no_defs"
EPSG = 3408


class Parcel():
    """Class to hold parcel trajectory"""

    def __init__(self, data, year, week_start='08-01'):
        row, column, concentration = zip(*zip(*(iter(data),) * 3))
        ntime = len(row)
        time = get_datetime(year, week_start, nweeks=ntime)
        x, y = to_projected_coordinates(column, row)
        self.time = time
        self.row = np.array(row)
        self.column = np.array(column)
        self.x = np.array(x)
        self.y = np.array(y)
        self.concentration = np.array(concentration)

    def __str__(self):
        """return str representation"""
        header = ['time', 'row', 'column', 'x', 'y', 'concentration']
        string = []
        string.append('-'*57+'\n')
        string.append(' '.join(header)+'\n')
        string.append('-'*57+'\n')
        zipped = zip(self.time,
                     self.row,
                     self.column,
                     self.x,
                     self.y,
                     self.concentration)
        for t, r, c, x, y, s in zipped:
            string.append(f'{t.strftime("%Y-%m-%d")} {r:7.3f} {c:7.3f} {x:11.3f} {y:11.3f} {s:5.1f}\n')
        return ''.join(string)


def to_projected_coordinates(col, row):
    fwd = Affine.from_gdal(*GEOTRANSFORM)
    xs = []
    ys = []
    for c, r in zip(col, row):
        if c < 999.0:
            x, y = fwd * (c, r)
        else:
            x, y = np.nan, np.nan
        xs.append(x)
        ys.append(y)
    return xs, ys


def get_datetime(year, week_start, nweeks=52):
    date_start = dt.datetime.strptime(f'{year}-{week_start}', '%Y-%m-%d')
    return [date_start + dt.timedelta(weeks=w) for w in range(nweeks)]


def load_parcels(filepath):
    year = filepath.split('_')[2][:4]
    with open(filepath, 'r', newline='') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',',
                               quoting=csv.QUOTE_NONNUMERIC)
        return [Parcel(data, year) for data in csvreader]


def stack_parcels(parcels):
    """Creates 2D (time, trajectory) arrays"""
    arr = np.stack([p.row for p in parcels], axis=1)


def to_xarray(parcels):
    dims = ['time', 'trajectory']
    ds = xr.Dataset({
        'row': (dims, np.stack([p.row for p in parcels], axis=1)),
        'col': (dims, np.stack([p.column for p in parcels], axis=1)),
        'x': (dims, np.stack([p.x for p in parcels], axis=1)),
        'y': (dims, np.stack([p.y for p in parcels], axis=1)),
        'concentration': (dims, np.stack([p.concentration for p in parcels], axis=1)),
        },
                    coords={
                        'time': parcels[0].time,
                        'trajectory': np.arange(len(parcels)),
                    })
    return ds


'''with zipfile.Zipfile("parcels.xyz.2019w40_2020w40.zip", "w") as archive:
    ...:     for idx, parcel in enumerate(parcels):
    ...:         if idx > 10: break
    ...:         filename = f'parcel{idx:06d}.csv'
    ...:         parcel.to_csv(filename)
    ...:         archive.write(filename)
'''
