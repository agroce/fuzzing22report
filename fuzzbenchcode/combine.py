import shutil

import pandas as pd

import requests

CSV_URLS = [
    'https://www.fuzzbench.com/reports/experimental/2022-10-13-um-final-1/data.csv.gz',
    'https://www.fuzzbench.com/reports/experimental/2022-10-13-um-final-2/data.csv.gz',
    'https://www.fuzzbench.com/reports/experimental/2022-10-13-um-final-5/data.csv.gz',
    'https://www.fuzzbench.com/reports/2022-09-29/data.csv.gz',
]

combined = []

for idx, url in enumerate(CSV_URLS):
    r = requests.get(url, stream=True)
    filename = f'{idx}.csv.gz'
    with open(filename, 'wb') as fp:
        shutil.copyfileobj(r.raw, fp)
    print(filename)
    df = pd.read_csv(filename, index_col=None, header=0)
    combined.append(df)
df = pd.concat(combined, axis=0, ignore_index=True)
df.to_csv('data.csv.gz')
