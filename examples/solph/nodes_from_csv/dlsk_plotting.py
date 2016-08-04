# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import cm


# global plotting options
plt.rcParams.update(plt.rcParamsDefault)
matplotlib.style.use('ggplot')
plt.rcParams['lines.linewidth'] = 2.5
plt.rcParams['axes.facecolor'] = 'silver'
plt.rcParams['xtick.color'] = 'k'
plt.rcParams['ytick.color'] = 'k'
plt.rcParams['text.color'] = 'k'
plt.rcParams['axes.labelcolor'] = 'k'
plt.rcParams.update({'font.size': 10})
plt.rcParams['image.cmap'] = 'Blues'

# read file
file = ('results/'
        'scenario_nep_2014_2016-08-04 11:28:11.690657_DE.csv')

df_raw = pd.read_csv(file, parse_dates=[0], index_col=0, keep_date_col=True)
df_raw.head()
df_raw.columns


# %% plot fundamental and regression prices

df = df_raw[['price_volatility', 'duals']]

df.plot()
plt.xlabel('Zeit in h')
plt.ylabel('Preis in EUR/MWh')
plt.show()

df[0:24 * 7 * 8].plot()
plt.xlabel('Zeit in h')
plt.ylabel('Preis in EUR/MWh')
plt.show()

df[['price_volatility', 'duals']].describe()


# %% polynom fitting: residual load

# prepare dataframe for fit
residual_load = df_raw['DE_load'] + df_raw['AT_load'] + df_raw['LU_load'] - \
                df_raw['DE_wind'] - df_raw['AT_wind'] - df_raw['LU_wind'] - \
                df_raw['DE_solar'] - df_raw['AT_solar'] - df_raw['LU_solar']

# real prices
price_real = pd.read_csv('price_eex_day_ahead_2014.csv')
price_real.index = df_raw.index

df = pd.concat([residual_load, price_real, df_raw['duals']], axis=1)
df.columns = ['res_load', 'price_real', 'price_model']

# fit polynom of 3rd degree to price_real(res_load)
z = np.polyfit(df['res_load'], df['price_real'], 3)
p = np.poly1d(z)
df['price_polynom_res_load'] = p(df['res_load'])

df.plot.scatter(x='res_load', y='price_real')
plt.plot(df['res_load'],
         (
          z[0] * df['res_load'] ** 3 +
          z[1] * df['res_load'] ** 2 +
          z[2] * df['res_load'] ** 1 +
          z[3]
          ), color='red')
plt.xlabel('Residuallast in MW')
plt.ylabel('Day-Ahead Preis in EUR/MWh')
plt.show()


# %% dispatch plot (balance doesn't fit since DE/LU/AT are one bidding area)

# country code
cc = 'DE'

# get fossil and renewable power plants
fuels = ['run_of_river', 'biomass', 'solar', 'wind', 'uranium', 'lignite',
         'hard_coal', 'gas', 'mixed_fuels', 'oil', 'load', 'excess',
         'shortage']

dispatch = pd.DataFrame()

for f in fuels:
    cols = [c for c in df_raw.columns if f in c and cc in c]
    dispatch[f] = df_raw[cols].sum(axis=1)

dispatch.index = df_raw.index

# get imports and exports and aggregate columns
cols = [c for c in df_raw.columns if 'powerline' in c]
powerlines = df_raw[cols]

exports = powerlines[[c for c in powerlines.columns
                      if c.startswith(cc + '_')]]

imports = powerlines[[c for c in powerlines.columns
                      if '_' + cc + '_' in c]]

dispatch['imports'] = imports.sum(axis=1)
dispatch['exports'] = exports.sum(axis=1)

# get imports and exports and aggregate columns
phs_in = df_raw[[c for c in df_raw.columns if 'phs_in' in c]]
phs_out = df_raw[[c for c in df_raw.columns if 'phs_out' in c]]
phs_level = df_raw[[c for c in df_raw.columns if 'phs_level' in c]]

dispatch['phs_in'] = phs_in.sum(axis=1)
dispatch['phs_out'] = phs_out.sum(axis=1)
dispatch['phs_level'] = phs_level.sum(axis=1)

# translation
dispatch_de = dispatch[
    ['run_of_river', 'biomass', 'solar', 'wind', 'uranium', 'lignite',
     'hard_coal', 'gas', 'storage_out', 'imports', 'exports']]
dispatch_de = dispatch_de.divide(1000)

# dict with new column names
en_de = {'run_of_river': 'Laufwasser',
         'biomass': 'Biomasse',
         'solar': 'Solar',
         'wind': 'Wind',
         'uranium': 'Kernenergie',
         'lignite': 'Braunkohle',
         'hard_coal': 'Steinkohle',
         'gas': 'Gas',
         'mixed_fuels': 'Sonstiges',
         'oil': 'Öl',
         'storage_out': 'Pumpspeicher',
         'imports': 'Import',
         'exports': 'Export',
         'load': 'Last'}
dispatch_de.rename(columns=en_de, inplace=True)

# area plot. gute woche: '2014-01-21':'2014-01-27'
dispatch_de[['Biomasse', 'Laufwasser', 'Kernenergie', 'Braunkohle',
             'Steinkohle', 'Gas', 'Solar', 'Wind',
             'Import']]['2014-01-21':'2014-01-27'] \
             .plot(kind='area', stacked=True, linewidth=0, legend='reverse',
                   cmap=cm.get_cmap('Spectral'))
plt.xlabel('Datum')
plt.ylabel('Leistung in  GW')
plt.ylim(0, max(dispatch_de.sum(axis=1)) * 1.3)
plt.show()

# duration curves (sort columns individually)
curves = pd.concat(
    [dispatch_de[col].sort_values(ascending=False).reset_index(drop=True)
     for col in dispatch_de], axis=1)
curves[['Kernenergie', 'Braunkohle',
        'Steinkohle', 'Gas', 'Solar', 'Wind',
        'Import', 'Export']].plot(cmap=cm.get_cmap('Spectral'))
plt.xlabel('Stunden des Jahres')
plt.ylabel('Leistung in GW')
plt.show()

# duration curves ordered by load (stacked) - storages to be added!
curves_stacked = pd.concat([dispatch_de,
                            dispatch['load'].divide(1000),
                            dispatch['imports'].divide(1000)],
                           axis=1)
curves_stacked = curves_stacked.sort_values(by=['load'], ascending=False)
curves_stacked.reset_index(drop=True, inplace=True)

curves_stacked[['Biomasse', 'Laufwasser', 'Kernenergie', 'Braunkohle',
                'Steinkohle', 'Gas', 'Solar', 'Wind',
                'Import']].plot(kind='area', stacked=True,
                                legend='reverse',
                                cmap=cm.get_cmap('Spectral'))
#plt.plot(curves_stacked['load'])
plt.xlabel('Stunden des Jahres geordnet nach der Last (rot)')
plt.ylabel('Leistung in GW')
plt.show()
