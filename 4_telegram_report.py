import telegram
import numpy as np
import matplotlib.pyplot as plt
from matplotlib_venn import venn2
import seaborn as sns
from datetime import date
import io
import logging
import pandas as pd
import pandahouse
from read_db.CH import Getch
import os


sns.set()


def telegram_report(chat=None):
    chat_id = chat or -674009613 
    # chat_id = chat or 187545653
    bot = telegram.Bot(token='***')
    
    # metrics 1
    stat_7days = Getch("select toDate(time) as date, \
    uniqExact(user_id) as user_cnt, \
    countIf(user_id, action='view') as view_cnt, \
    countIf(user_id, action='like') as like_cnt, \
    countIf(user_id, action='like')/countIf(user_id, action='view')*100 as ctr \
    from simulator_20211220.feed_actions \
    where toDate(time) between today()-7 and today()-1 \
    group by toDate(time) \
    order by toDate(time)").df
    
    msg = 'News feed report for: <b>' + pd.to_datetime(str(stat_7days['date'].values[-1])).strftime("%m/%d/%Y") + '</b>' + '\n' + '\n' + \
    '<b>DAU</b> = ' + str(stat_7days['user_cnt'].values[-1]) + '\n' + \
    '<b>CTR</b> = ' + str(round(stat_7days['ctr'].values[-1],2))+ '%' + '\n' + \
    '<b>Views</b> = ' + str(stat_7days['view_cnt'].values[-1]) + '\n' + \
    '<b>Likes</b> = ' + str(stat_7days['like_cnt'].values[-1]) + '\n' + '\n' + \
    'Full versions of the report can be found here:' + '\n' + \
    '- <a href="http://superset.lab.karpov.courses/r/400">News feed - basic</a>' + '\n' + \
    '- <a href="http://superset.lab.karpov.courses/r/401">News feed & Messenger</a>'  
    
    
    # plot 1
    fig = plt.figure(figsize=(20, 12))
    fig.suptitle('News feed | Report for ' + pd.to_datetime(str(stat_7days['date'].values[0])).strftime("%m/%d/%Y") + \
             ' - ' + pd.to_datetime(str(stat_7days['date'].values[-1])).strftime("%m/%d/%Y"),  fontsize=18)

    ax1 = fig.add_subplot(2,2,1)
    ax1.set_title('DAU')
    ax1.set_facecolor('white')
    ax1.grid(True)
    ax1.plot(stat_7days['date'], stat_7days['user_cnt'], 'darkcyan')
    plt.setp(ax1.get_xticklabels(), visible=False)

    ax2 = fig.add_subplot(2,2,2)
    ax2.set_title('CTR')
    ax2.set_facecolor('white')
    ax2.grid(True)
    ax2.plot(stat_7days['date'], stat_7days['ctr'], 'navy')
    plt.setp(ax2.get_xticklabels(), visible=False)

    ax3 = fig.add_subplot(2,2,3)
    ax3.set_title('Views')
    ax3.set_facecolor('white')
    ax3.grid(True)
    ax3.plot(stat_7days['date'], stat_7days['view_cnt'], 'royalblue')

    ax4 = fig.add_subplot(2,2,4)
    ax4.set_title('Likes')
    ax4.set_facecolor('white')
    ax4.grid(True)
    ax4.plot(stat_7days['date'], stat_7days['like_cnt'], 'cornflowerblue')
    
    caption = 'News feed | Report for ' + pd.to_datetime(str(stat_7days['date'].values[0])).strftime("%m/%d/%Y") + \
             ' - ' + pd.to_datetime(str(stat_7days['date'].values[-1])).strftime("%m/%d/%Y")

    plot_object = io.BytesIO()
    fig.savefig(plot_object)
    plot_object.seek(0)
    plot_object.name = 'full_figure.png'
    plt.show()
    plt.close()
    
    # service users
    service_users = Getch("SELECT uniqExactIf(fa.user_id, ma.user_id=0) as fa_user_cnt, \
    uniqExactIf(ma.user_id, fa.user_id=0) as ma_user_cnt, \
    uniqExactIf(ma.user_id, and(fa.user_id>0, ma.user_id>0)) as active_user_cnt \
    from simulator_20211220.feed_actions as fa \
    full JOIN \
    simulator_20211220.message_actions as ma \
    on ma.user_id=fa.user_id").df
    
    # df with avg values
    avg_scores = Getch("select \
        fa.date,  \
        fa_user_cnt, \
        ma_user_cnt, \
        view_cnt, \
        like_cnt, \
        message_cnt \
    from ( \
    select toDate(time) as date,  \
        uniqExact(user_id) as fa_user_cnt,  \
        countIf(user_id, action='view') as view_cnt, \
        countIf(user_id, action='like') as like_cnt \
    from simulator_20211220.feed_actions \
    group by toDate(time)) as fa \
    left join (select  \
        toDate(time) as date,  \
        uniqExact(user_id) as ma_user_cnt,  \
        count(user_id) as message_cnt \
        from simulator_20211220.message_actions \
        group by toDate(time) \
    ) as ma \
    on fa.date=ma.date").df 

    avg_scores['views_avg'] = round(avg_scores['view_cnt']/avg_scores['fa_user_cnt'],2)
    avg_scores['likes_avg'] = round(avg_scores['like_cnt']/avg_scores['fa_user_cnt'],2)
    avg_scores['messages_avg'] = round(avg_scores['message_cnt']/avg_scores['ma_user_cnt'],2)

    # plot2
    fig = plt.figure(figsize=(20, 12))
    fig.suptitle('New feed & Messenger | Report on ' + date.today().strftime("%Y-%m-%d"))


    ax1 = fig.add_subplot(2,2,1)
    ax1.set_title('Users of service')
    venn2(subsets = (service_users['fa_user_cnt'][0], service_users['ma_user_cnt'][0], service_users['active_user_cnt'][0]), 
          set_labels = ('News feed users', 'Messenger users'),
          set_colors=('blue', 'darkviolet'))

    ax2 = fig.add_subplot(2,2,2)
    ax2.set_title('Events')
    ax2.set_facecolor('white')
    ax2.grid(True)
    ax2.plot(avg_scores['date'], avg_scores['view_cnt'], color='royalblue', label='views')
    ax2.plot(avg_scores['date'], avg_scores['like_cnt'], color='cornflowerblue', label='likes')
    ax2.plot(avg_scores['date'], avg_scores['message_cnt'], color='mediumorchid', label='messages')
    ax2.legend(edgecolor=(0, 0, 0, 1.), facecolor=(1, 1, 1, 0.1))

    ax3 = fig.add_subplot(2,2,3)
    ax3.set_title('Users of each service')
    ax3.set_facecolor('white')
    ax3.grid(True)
    ax3.plot(avg_scores['date'], avg_scores['fa_user_cnt'], color='blue', label='News feed users')
    ax3.plot(avg_scores['date'], avg_scores['ma_user_cnt'], color='darkviolet', label='Messenger users')
    ax3.legend(edgecolor=(0, 0, 0, 1.), facecolor=(1, 1, 1, 0.1))
    plt.setp(ax2.get_xticklabels(), visible=False)

    ax4 = fig.add_subplot(2,2,4)
    ax4.set_title('AVG events per user')
    ax4.set_facecolor('white')
    ax4.grid(True)
    ax4.plot(avg_scores['date'], avg_scores['views_avg'], color='royalblue', label='AVG views')
    ax4.plot(avg_scores['date'], avg_scores['likes_avg'], color='cornflowerblue', label='AVG likes')
    ax4.plot(avg_scores['date'], avg_scores['messages_avg'], color='mediumorchid', label='AVG messages')
    ax4.legend(edgecolor=(0, 0, 0, 1.), facecolor=(1, 1, 1, 0.1))

    plot_object2 = io.BytesIO()
    fig.savefig(plot_object2)
    plot_object2.seek(0)
    plot_object2.name = 'full_figure2.png'
    plt.show()
    plt.close()
    
    caption2 = 'New feed & Messenger | Report on ' + date.today().strftime("%m/%d/%Y")
    
    #file
    file_object = io.BytesIO()
    avg_scores.to_excel(file_object)
    file_object.name = 'report_' + date.today().strftime("%d-%m-%Y") + '.xlsx'
    file_object.seek(0)
    
    bot.sendMessage(chat_id = chat_id, text = msg, parse_mode=telegram.ParseMode.HTML)
    bot.sendPhoto(chat_id=chat_id, photo=plot_object, caption=caption)
    bot.sendPhoto(chat_id=chat_id, photo=plot_object2, caption=caption2)
    bot.sendDocument(chat_id=chat_id, document=file_object)


try:
    telegram_report()
except Exception as e:
    print(e)
