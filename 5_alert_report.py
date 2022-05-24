import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import telegram
import pandahouse
from datetime import date
import io
from read_db.CH import Getch
import sys
import os

def check_anomaly(df, df_today, metric):
    hm_max_today_idx = len(df_today)-1
    dict_15mins = {}
    for i in range(len(df)):
        if df['hm_15min'][i] in dict_15mins.keys():
            dict_15mins[df['hm_15min'][i]].append(df[metric].values[i])
        else:
            dict_15mins[df['hm_15min'][i]]=[df[metric][i]] 
    df_15mins = pd.DataFrame.from_dict(dict_15mins)
    
    # find outlier in every hm group, remove them
    # create dict with hm and array of values
    dict_means_15mins = {}
    for hm_15min in df_15mins.columns:
        hm_15min_values_list = df_15mins[hm_15min].values.tolist()
        iqr = pd.Series(df_15mins[hm_15min]).quantile(0.75)-pd.Series(df_15mins[hm_15min]).quantile(0.25)
        for i in range(len(df_15mins)):
            if df_15mins[hm_15min][i]<pd.Series(df_15mins[hm_15min]).quantile(0.25)-1.5*iqr \
                or df_15mins[hm_15min][i]>pd.Series(df_15mins[hm_15min]).quantile(0.75)+1.5*iqr:
                    hm_15min_values_list.remove(df_15mins[hm_15min][i])
        dict_means_15mins[hm_15min] = [round(np.mean(hm_15min_values_list),2), np.median(hm_15min_values_list),
                                      round(np.std(hm_15min_values_list),2), len(hm_15min_values_list)]
    
    df_means_15mins = pd.DataFrame.from_dict(dict_means_15mins)
    df_means_15mins = df_means_15mins.transpose().reset_index()
    df_means_15mins.columns = ['hm_15min', 'mean', 'median', 'std', 'n']
    df_means_15mins['se'] = round(df_means_15mins['std']/(df_means_15mins['n']**(1/2)),2)
    df_means_15mins['ci_low_95'] = round(df_means_15mins['mean'] - df_means_15mins['se']*1.96,2)
    df_means_15mins['ci_up_95'] = round(df_means_15mins['mean'] + df_means_15mins['se']*1.96,2)
    df_means_15mins['sigma_low'] = round(df_means_15mins['mean'] - df_means_15mins['std']*3,2)
    df_means_15mins['sigma_up'] = round(df_means_15mins['mean'] + df_means_15mins['std']*3,2)
    
    df_all = df_means_15mins.merge(df_today, how='left', on='hm_15min').drop(columns=['ts','date'])
    
    current_value = df_all[metric][hm_max_today_idx]
    pred_value = df_all['mean'][hm_max_today_idx]
    
    # check if current_value is out of borders
    if current_value<df_all['sigma_low'][hm_max_today_idx]:
        diff = round(current_value / df_all['sigma_low'][hm_max_today_idx] - 1,2)
        is_alert = 1
    elif current_value>df_all['sigma_up'][hm_max_today_idx]:
        diff = round(current_value / df_all['sigma_up'][hm_max_today_idx] - 1,2)
        is_alert = 1
    else:
        diff = round(current_value / df_all['mean'][hm_max_today_idx] - 1,2)
        is_alert = 0


    return is_alert, current_value, diff, df_all

def run_alerts(chat=None):
    # chat_id = chat or 187545653
    chat_id = chat or -701443838
    bot = telegram.Bot(token='5029891106:AAFyzHPo3PufBPunqVTs6OxNzuW8xc08dK0')

    # get data for last month
    data = Getch(''' SELECT
        fa.ts,
        fa.date,
        fa.hm_15min,
        fa.user_feed_cnt,
        fa.view_cnt,
        fa.like_cnt,
        ma.message_cnt
    FROM ( 
        select toStartOfFifteenMinutes(time) as ts 
        , toDate(ts) as date
        , formatDateTime(ts, '%R') as hm_15min
        , uniqExact(user_id) as user_feed_cnt
        , countIf(user_id, action='view') as view_cnt
        , countIf(user_id, action='like') as like_cnt
    from simulator_20211220.feed_actions
    WHERE ts >=  today() - 30 and ts < today()
    GROUP BY ts, date, hm_15min
    ORDER BY ts) as fa
    left join (
        select 
        toStartOfFifteenMinutes(time) as ts 
        , toDate(ts) as date
        , formatDateTime(ts, '%R') as hm_15min
        , count(user_id) as message_cnt
    FROM simulator_20211220.message_actions
    WHERE ts >=  today() - 30 and ts < today()
    GROUP BY ts, date, hm_15min
    ORDER BY ts
    ) as ma
    on ma.date=fa.date and ma.hm_15min=fa.hm_15min
    ORDER BY ts ''').df
    
    # get data for today
    data_today = Getch(''' SELECT
        fa.ts,
        fa.date,
        fa.hm_15min,
        fa.user_feed_cnt,
        fa.view_cnt,
        fa.like_cnt,
        ma.message_cnt
    FROM ( 
        select toStartOfFifteenMinutes(time) as ts 
        , toDate(ts) as date
        , formatDateTime(ts, '%R') as hm_15min
        , uniqExact(user_id) as user_feed_cnt
        , countIf(user_id, action='view') as view_cnt
        , countIf(user_id, action='like') as like_cnt
    from simulator_20211220.feed_actions
    WHERE ts >= today() and ts < toStartOfFifteenMinutes(now())
    GROUP BY ts, date, hm_15min
    ORDER BY ts) as fa
    left join (
        select 
        toStartOfFifteenMinutes(time) as ts 
        , toDate(ts) as date
        , formatDateTime(ts, '%R') as hm_15min
        , count(user_id) as message_cnt
    FROM simulator_20211220.message_actions
    WHERE ts >= today() and ts < toStartOfFifteenMinutes(now())
    GROUP BY ts, date, hm_15min
    ORDER BY ts
    ) as ma
    on ma.date=fa.date and ma.hm_15min=fa.hm_15min
    ORDER BY ts ''').df
    
    
    metrics = {'user_feed_cnt':'Users', 'view_cnt':'Views', 'like_cnt':'Likes', 'message_cnt':'Messages'}
    for metric, metric_nm in metrics.items():
        is_alert, current_value, diff, df_all = check_anomaly(data, data_today, metric)
        
        if is_alert==1 and abs(diff)>0.3:
            msg = '''❗️❗️❗️<b>ALARM</b>❗️❗️❗️ \nMetric - <b>{metric}</b>:\nCurrent value = <b>{current_value}</b>\nDeviation = <b>{diff:.2%}</b>'''.format(metric=metric_nm, current_value=current_value,diff=diff)

            sns.set(rc={'figure.figsize': (12, 6)}) 
            plt.tight_layout()

            ax = sns.lineplot( 
                x=df_all['hm_15min'], y=df_all[metric], color='navy', label="current value"
                )

            ax = sns.lineplot( 
                x=df_all['hm_15min'], y=df_all['sigma_low'], color='darkred', label='border'
                )

            ax = sns.lineplot(
                x=df_all['hm_15min'], y=df_all['sigma_up'], color='darkred'
                )


            for ind, label in enumerate(ax.get_xticklabels()): 
                if ind % 15 == 0:
                    label.set_visible(True)
                else:
                    label.set_visible(False)

            ax.set(xlabel='time')
            ax.set(ylabel=metric_nm) 
            ax.grid(True)
            ax.set_facecolor('white')
            ax.legend(edgecolor=(0, 0, 0, 1.), facecolor=(1, 1, 1, 0.1))

            ax.set_title('{}'.format(metric_nm)) 
            ax.set(ylim=(0, None))
            
            plot_object = io.BytesIO()
            ax.figure.savefig(plot_object)
            plot_object.seek(0)
            plot_object.name = '{0}.png'.format(metric_nm)
            # plt.show()
            plt.close()
            

            # send alert message
            bot.sendMessage(chat_id=chat_id, text=msg, parse_mode=telegram.ParseMode.HTML)
            bot.sendPhoto(chat_id=chat_id, photo=plot_object)
            
try:
    run_alerts()
except Exception as e:
    print(e)
